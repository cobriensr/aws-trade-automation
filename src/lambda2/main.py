"""Secondary Lambda function for symbol lookup."""

import json
import logging
import time
import traceback
from typing import Dict
from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError
import psutil
import boto3
import databento as db

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
cloudwatch = boto3.client('cloudwatch')
ssm = boto3.client("ssm")

class SymbolLookupError(Exception):
    """Custom exception for symbol lookup errors"""

def publish_metric(name: str, value: float = 1, unit: str = 'Count') -> None:
    """Publish a metric to CloudWatch"""
    try:
        cloudwatch.put_metric_data(
            Namespace='Trading/SymbolLookup',
            MetricData=[{
                'MetricName': name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.now(timezone.utc)
            }]
        )
    except Exception as e:
        logger.error(f"Failed to publish metric {name}: {str(e)}")

def configure_logger(context) -> None:
    """Configure logger with enhanced Lambda context information"""
    formatter = logging.Formatter(
        "[%(levelname)s] %(asctime)s.%(msecs)03d "
        f"RequestId: {context.aws_request_id} "
        "%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.handlers.clear()
    log_handler = logging.StreamHandler()
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)

    logger.info(f"Log Group: {context.log_group_name}")
    logger.info(f"Log Stream: {context.log_stream_name}")
    logger.info(f"Function Memory: {context.memory_limit_in_mb}MB")
    logger.info(f"Remaining Time: {context.get_remaining_time_in_millis()}ms")

def get_api_key() -> str:
    """Get Databento API key with enhanced error handling"""
    try:
        response = ssm.get_parameter(
            Name="/tradovate/DATABENTO_API_KEY",
            WithDecryption=True
        )
        api_key = response["Parameter"]["Value"]
        publish_metric('api_key_retrieval_success')
        return api_key
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        logger.error(f"AWS SSM error retrieving API key: {error_code} - {str(e)}")
        publish_metric('api_key_retrieval_error')
        raise SymbolLookupError("Failed to retrieve Databento API key from all sources") from e
        
    except Exception as e:
        logger.error(f"Unexpected error retrieving API key: {str(e)}")
        publish_metric('api_key_retrieval_error')
        raise SymbolLookupError(f"API key retrieval failed: {str(e)}") from e

def get_previous_business_day(from_date: datetime, lookback_days: int = 1) -> datetime:
    """Get the previous business day (Mon-Fri), looking back a specified number of days"""
    business_days_found = 0
    current_date = from_date
    
    while business_days_found < lookback_days:
        current_date = current_date - timedelta(days=1)
        if current_date.weekday() <= 4:  # Monday through Friday
            business_days_found += 1
            
    return current_date

def get_historical_data_dict(api_key: str) -> Dict:
    """Get historical data with comprehensive error handling and metrics"""
    start_time = time.time()
    
    try:
        # Get the previous business day (look back 2 days to ensure we're before the data cutoff)
        today = datetime.now()
        previous_business_day = get_previous_business_day(today, lookback_days=2)
        next_day = previous_business_day + timedelta(days=1)
        
        # Use previous business day as start and next day as end
        data_start = previous_business_day.strftime("%Y-%m-%d")
        data_end = next_day.strftime("%Y-%m-%d")
        
        logger.info(f"Fetching data for range: {data_start} to {data_end}")

        # Symbol mapping with versioning
        databento_mapping = {
            "MES.n.0": "MES1!",  # E-Mini S&P 500
            "MNQ.n.0": "MNQ1!",  # E-Mini NASDAQ 100
            "YM.n.0": "YM1!",    # E-Mini Dow
            "RTY.n.0": "RTY1!",  # E-Mini Russell 2000
            "NG.n.0": "NG1!",    # Natural Gas
            "GC.n.0": "GC1!",    # Gold
            "CL.n.0": "CL1!",    # Crude Oil
        }
        
        # Initialize Databento client with timeout handling
        db_client = db.Historical(api_key)
        
        try:
            # Get historical data
            df = db_client.timeseries.get_range(
                dataset="GLBX.MDP3",
                schema="definition",
                stype_in="continuous",
                symbols=list(databento_mapping.keys()),  # Use Databento symbols (GC.n.0 etc)
                start=data_start,
                end=data_end,
            ).to_df()
        except db.BentoServerError as e:
            publish_metric('databento_server_error')
            logger.error(f"Databento server error: {str(e)}")
            logger.error(f"Request ID: {e.request_id}")
            raise SymbolLookupError(f"Databento server error: {str(e)}") from e
        except db.BentoClientError as e:
            publish_metric('databento_client_error')
            logger.error(f"Databento client error: {str(e)}")
            logger.error(f"Request ID: {e.request_id}")
            raise SymbolLookupError(f"Databento client error: {str(e)}") from e
        except db.BentoError as e:
            publish_metric('databento_general_error')
            logger.error(f"Databento error: {str(e)}")
            raise SymbolLookupError(f"Databento error: {str(e)}") from e

        if df.empty:
            raise SymbolLookupError("No data returned from Databento API")

                # Process the data
        df["date"] = df.index.date
        pivoted = df.pivot(index="date", columns="symbol", values="raw_symbol")
        
        if pivoted.empty:
            raise SymbolLookupError("Failed to process symbol data")
            
        # Get latest data and map symbols with detailed logging
        latest_data = pivoted.iloc[-1].to_dict()
        logger.info(f"Raw latest data: {latest_data}")  # Debug log
        
        result = {}
        for k, v in latest_data.items():
            tradovate_symbol = databento_mapping.get(k)
            if tradovate_symbol:
                logger.info(f"Mapping {k} -> {tradovate_symbol} = {v}")
                result[tradovate_symbol] = v
            else:
                logger.warning(f"No mapping found for Databento symbol: {k}")

        # Validate result
        if not result:
            raise SymbolLookupError("No symbols mapped in result")
            
        logger.info(f"Final symbol mapping: {json.dumps(result)}")  # Debug log
            
        # Record success metrics
        duration = (time.time() - start_time) * 1000
        publish_metric('databento_request_duration', duration, 'Milliseconds')
        publish_metric('databento_request_success')
        publish_metric('symbols_mapped', len(result))
        
        logger.info(f"Successfully mapped {len(result)} symbols")
        return result
        
    except Exception as e:
        publish_metric('symbol_lookup_error')
        logger.error(f"Symbol lookup error: {str(e)}")
        logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
        raise SymbolLookupError(f"Failed to get historical data: {str(e)}") from e

def lambda_handler(event, context) -> Dict:
    """Lambda handler with comprehensive error handling and monitoring"""
    request_id = context.aws_request_id
    start_time = time.time()
    
    try:
        # Configure logging
        configure_logger(context)
        logger.info(f"Processing request {request_id}")
        logger.debug(f"Event: {json.dumps(event, indent=2)}")

        # Get API key
        api_key = get_api_key()
        
        # Get symbol mapping
        symbol_mapping = get_historical_data_dict(api_key)
        
        # Log symbol mapping
        logger.info(f"Symbol mapping result: {json.dumps(symbol_mapping)}")
        
        # Record success response
        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "success",
                "data": symbol_mapping,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        }
        
    except SymbolLookupError as e:
        logger.error(f"Symbol lookup error in request {request_id}: {str(e)}")
        return {
            "statusCode": 400,
            "body": json.dumps({
                "status": "error",
                "error": str(e),
                "request_id": request_id
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in request {request_id}: {str(e)}")
        logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "error",
                "error": "Internal server error",
                "request_id": request_id
            })
        }
        
    finally:
        # Calculate and record duration
        duration = (time.time() - start_time) * 1000
        publish_metric('request_duration', duration, 'Milliseconds')
        
        # Log request completion
        log_message = f"Request {request_id} completed in {duration:.2f}ms"
        if duration > 5000:
            logger.warning(f"{log_message} - Request took longer than 5 seconds")
        else:
            logger.info(log_message)
        
        # Monitor resources
        remaining_time = context.get_remaining_time_in_millis()
        if remaining_time < 1000:
            logger.warning(f"Low remaining execution time: {remaining_time}ms")
            
        try:
            memory_used = psutil.Process().memory_info().rss / 1024 / 1024  # Convert to MB
            publish_metric('memory_used', memory_used, 'Megabytes')
            memory_limit = float(context.memory_limit_in_mb)  # Convert to float
            threshold = int(memory_limit * 0.9)  # Convert the threshold to integer
            if memory_used > threshold:
                logger.warning(f"High memory usage: {memory_used:.2f}MB")
        except ImportError:
            logger.warning("psutil not available - memory monitoring disabled")
        except Exception as e:
            logger.error(f"Error monitoring memory usage: {str(e)}")