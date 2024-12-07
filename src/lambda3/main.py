"""Secondary Lambda function for symbol lookup."""

import os
import json
import uuid
import logging
from typing import Dict, Tuple
from pathlib import Path
from dotenv import load_dotenv
import boto3
from aws_lambda_typing.events import APIGatewayProxyEventV2
from aws_lambda_typing.context import Context
from coinbase.rest import RESTClient

MIN_ORDER = {
    "BTCUSD": 0.01,
    "ETHUSD": 0.01,
    "XRPUSD": 0.01,
    "HBARUSD": 1,
    "SOLUSD": 0.01,
    "DOGEUSD": 1,
}

# AVG_ORDER_SIZE = {
#     "BTCUSD": "$993.00",
#     "ETHUSD": "$39.94",
#     "XRPUSD": "$.243",
#     "HBARUSD": "$.344",
#     "SOLUSD": "$2.3533",
#     "DOGEUSD": "$.433",
# }

def generate_order_id():
    return str(uuid.uuid4())

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def configure_logger(context: Context) -> None:
    """Configure logger with Lambda context information"""
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

def get_api_key() -> Tuple[str, str]:
    """Get Databento API key from Parameter Store"""
    try:
        ssm = boto3.client("ssm")
        api_key = ssm.get_parameter(
            Name="/tradovate/COINBASE_API_KEY_NAME",
            WithDecryption=True
        )["Parameter"]["Value"]
        api_secret = ssm.get_parameter(
            Name="/tradovate/COINBASE_PRIVATE_KEY",
            WithDecryption=True
        )["Parameter"]["Value"]
        return api_key, api_secret
    except Exception as exc:
        # If Parameter Store fails, try local .env (development)
        load_dotenv(Path(__file__).parents[2] / ".env")
        api_key = os.getenv("COINBASE_API_KEY_NAME")
        api_secret = os.getenv("COINBASE_PRIVATE_KEY")
        if not all([api_key, api_secret]):
            raise ValueError(
                "Could not load credentials from Parameter Store or .env"
            ) from exc
        return api_key, api_secret

def place_buy_order(api_key: str, api_secret: str, symbol: str) -> Dict:
    """
    Place a market order to buy.
    
    Args:
        api_key (str): Coinbase API key
        api_secret (str): Coinbase API secret
        symbol (str): Trading symbol (e.g., 'BTCUSD')
    
    Returns:
        Dict: Response containing order status and details
        
    Raises:
        Exception: If any critical error occurs during order placement
    """
    try:
        logger.info(f"Initiating buy order for symbol: {symbol}")
        
        # Initialize REST client
        client = RESTClient(api_key=api_key, api_secret=api_secret)
        logger.debug("REST client initialized successfully")
        
        # Set order size and format symbol
        if symbol not in MIN_ORDER:
            logger.error(f"Invalid symbol received: {symbol}")
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Invalid symbol",
                    "details": f"Symbol must be one of: {list(MIN_ORDER.keys())}"
                })
            }
        size = MIN_ORDER[symbol]
        formatted_symbol = f"{symbol[:3]}-{symbol[3:]}"
        logger.info(f"Order parameters - Size: {size}, Formatted Symbol: {formatted_symbol}")
        
        # Generate order ID
        order_id = generate_order_id()
        logger.info(f"Generated order ID: {order_id}")
        
        # Place buy order
        try:
            order = client.market_order_buy(
                client_order_id=order_id,
                product_id=formatted_symbol,
                base_size=str(size)
            )
            logger.info(f"Order placement response received: {json.dumps(order)}")
        except Exception as e:
            logger.error(f"Failed to place market order: {str(e)}")
            return {
                "success": False,
                "error": "Order placement failed",
                "details": str(e)
            }
        
        # Process order response
        if hasattr(order, 'success_response'):
            try:
                order_id = order.success_response.order_id
                fills = client.get_fills(order_id=order_id)
                fill_details = fills.to_dict()
                
                logger.info(f"Order successful - Order ID: {order_id}")
                logger.debug(f"Fill details: {json.dumps(fill_details, indent=2)}")
                
                return {
                    "success": True,
                    "order_id": order_id,
                    "fills": fill_details
                }
            except Exception as e:
                logger.error(f"Failed to process fills for order {order_id}: {str(e)}")
                return {
                    "success": True,
                    "order_id": order_id,
                    "error": "Fill retrieval failed",
                    "details": str(e)
                }
        elif hasattr(order, 'error_response'):
            error_msg = order.error_response
            logger.error(f"Order placement failed: {error_msg}")
            return {
                "success": False,
                "error": "Order failed",
                "details": error_msg
            }
            
    except Exception as e:
        logger.error(f"Unexpected error in place_buy_order: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": "Critical error",
            "details": str(e)
        }

def place_sell_order(api_key: str, api_secret: str, symbol: str) -> Dict:
    """
    Place a market order to sell.
    
    Args:
        api_key (str): Coinbase API key
        api_secret (str): Coinbase API secret
        symbol (str): Trading symbol (e.g., 'BTCUSD')
    
    Returns:
        Dict: Response containing order status and details
        
    Raises:
        Exception: If any critical error occurs during order placement
    """
    try:
        logger.info(f"Initiating sell order for symbol: {symbol}")
        
        # Initialize REST client
        client = RESTClient(api_key=api_key, api_secret=api_secret)
        logger.debug("REST client initialized successfully")
        
        # Set order size and format symbol
        if symbol not in MIN_ORDER:
            logger.error(f"Invalid symbol received: {symbol}")
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Invalid symbol",
                    "details": f"Symbol must be one of: {list(MIN_ORDER.keys())}"
                })
            }
        size = MIN_ORDER[symbol]
        formatted_symbol = f"{symbol[:3]}-{symbol[3:]}"
        logger.info(f"Order parameters - Size: {size}, Formatted Symbol: {formatted_symbol}")
        
        # Generate order ID
        order_id = generate_order_id()
        logger.info(f"Generated order ID: {order_id}")
        
        # Place sell order
        try:
            order = client.market_order_sell(
                client_order_id=order_id,
                product_id=formatted_symbol,
                base_size=str(size)
            )
            logger.info(f"Order placement response received: {json.dumps(order)}")
        except Exception as e:
            logger.error(f"Failed to place market order: {str(e)}")
            return {
                "success": False,
                "error": "Order placement failed",
                "details": str(e)
            }
        # Process order response
        if hasattr(order, 'success_response'):
            try:
                order_id = order.success_response.order_id
                fills = client.get_fills(order_id=order_id)
                fill_details = fills.to_dict()
                
                logger.info(f"Order successful - Order ID: {order_id}")
                logger.debug(f"Fill details: {json.dumps(fill_details, indent=2)}")
                
                return {
                    "success": True,
                    "order_id": order_id,
                    "fills": fill_details
                }
            except Exception as e:
                logger.error(f"Failed to process fills for order {order_id}: {str(e)}")
                return {
                    "success": True,
                    "order_id": order_id,
                    "error": "Fill retrieval failed",
                    "details": str(e)
                }
        elif hasattr(order, 'error_response'):
            error_msg = order.error_response
            logger.error(f"Order placement failed: {error_msg}")
            return {
                "success": False,
                "error": "Order failed",
                "details": error_msg
            }
            
    except Exception as e:
        logger.error(f"Unexpected error in place_sell_order: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": "Critical error",
            "details": str(e)
        }

def close_position(api_key: str, api_secret: str, symbol: str) -> Dict:
    """
    Close an open position.
    
    Args:
        api_key (str): Coinbase API key
        api_secret (str): Coinbase API secret
        symbol (str): Trading symbol (e.g., 'BTCUSD')
    
    Returns:
        Dict: Response containing order status and details
        
    Raises:
        Exception: If any critical error occurs during order placement
    """
    try:
        logger.info(f"Closing position for symbol: {symbol}")
        
        # Initialize REST client
        client = RESTClient(api_key=api_key, api_secret=api_secret)
        logger.debug("REST client initialized successfully")
        
        # Format symbol
        formatted_symbol = f"{symbol[:3]}-{symbol[3:]}"
        logger.info(f"Order parameters - Formatted Symbol: {formatted_symbol}")
        
        # Close position
        try:
            order = client.close_position(
                client_order_id=generate_order_id(),
                product_id=formatted_symbol,
            )
            logger.info(f"Order placement response received: {json.dumps(order)}")
        except Exception as e:
            logger.error(f"Failed to place market order: {str(e)}")
            return {
                "success": False,
                "error": "Order placement failed",
                "details": str(e)
            }
        # Process order response
        if hasattr(order, 'success_response'):
            try:
                order_id = order.success_response.order_id
                fills = client.get_fills(order_id=order_id)
                fill_details = fills.to_dict()
                
                logger.info(f"Order successful - Order ID: {order_id}")
                logger.debug(f"Fill details: {json.dumps(fill_details, indent=2)}")
                
                return {
                    "success": True,
                    "order_id": order_id,
                    "fills": fill_details
                }
            except Exception as e:
                logger.error(f"Failed to process fills for order {order_id}: {str(e)}")
                return {
                    "success": True,
                    "order_id": order_id,
                    "error": "Fill retrieval failed",
                    "details": str(e)
                }
        elif hasattr(order, 'error_response'):
            error_msg = order.error_response
            logger.error(f"Order placement failed: {error_msg}")
            return {
                "success": False,
                "error": "Order failed",
                "details": error_msg
            }
            
    except Exception as e:
        logger.error(f"Unexpected error in place_sell_order: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": "Critical error",
            "details": str(e)
        }

def list_orders(api_key: str, api_secret: str, symbol: str) -> Dict:
    """
    List open orders for a given symbol.

    Args:
        api_key (str): Coinbase API key
        api_secret (str): Coinbase API secret 
        symbol (str): Trading symbol (e.g., 'BTCUSD')

    Returns:
        Dict: Response containing orders and status details
    """
    try:
        logger.info(f"Retrieving orders for symbol: {symbol}")
        
        # Initialize REST client
        client = RESTClient(api_key=api_key, api_secret=api_secret)
        logger.debug("REST client initialized successfully")

        # Format symbol
        formatted_symbol = f"{symbol[:3]}-{symbol[3:]}"
        logger.info(f"Formatted Symbol: {formatted_symbol}")

        try:
            orders = client.list_orders(
                product_ids=[formatted_symbol],
                product_type="SPOT",
                order_types=["MARKET"],
                limit=1,
                sort_by="LAST_FILL_TIME"
            )
            logger.info(f"Orders retrieved successfully for {formatted_symbol}")
            
            # Convert orders to dictionary for return
            orders_dict = orders.to_dict()
            logger.debug(f"Orders details: {json.dumps(orders_dict, indent=2)}")
            
            return {
                "success": True,
                "orders": orders_dict
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve orders: {str(e)}")
            return {
                "success": False,
                "error": "Order retrieval failed",
                "details": str(e)
            }
            
    except Exception as e:
        logger.error(f"Unexpected error in list_orders: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": "Critical error",
            "details": str(e)
        }

def lambda_handler(event: APIGatewayProxyEventV2, context: Context) -> Dict:
    """
    Lambda handler for processing trading signals and executing orders.
    
    Args:
        event (APIGatewayProxyEventV2): API Gateway event
        context (Context): Lambda context
    
    Returns:
        Dict: API Gateway response
    """
    try:
        # Configure logging at the start of execution
        configure_logger(context)
        
        # Log received event
        logger.debug(f"Received event: {json.dumps(event, indent=2)}")
        
        # Get the request path from the event
        path = event.get("rawPath", event.get("path", ""))
        logger.info(f"Received request for path: {path}")
        
        try:
            # Parse webhook
            webhook_data = json.loads(event["body"])
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse webhook data: {str(e)}")
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Invalid webhook data format",
                    "details": str(e)
                })
            }

        try:
            # Get API key and secret from Parameter Store
            api_key, api_secret = get_api_key()
        except Exception as e:
            logger.error(f"Failed to retrieve API credentials: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": "Failed to retrieve API credentials",
                    "details": str(e)
                })
            }
        
        # Extract trading information
        try:
            symbol = webhook_data["market_data"]["symbol"]
            direction = webhook_data["signal"]["direction"]
            logger.info(f"Processing {direction} signal for {symbol}")
        except KeyError as e:
            logger.error(f"Missing required field in webhook data: {str(e)}")
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Missing required field in webhook data",
                    "details": str(e)
                })
            }

        # Get open orders for the symbol
        orders_response = list_orders(api_key, api_secret, symbol)
                
        # Only try to close positions if we successfully got orders AND there are orders to close
        if orders_response["success"] and orders_response["orders"]:
            logger.info(f"Found existing orders for {symbol}, attempting to close positions")
            close_response = close_position(api_key, api_secret, symbol)
            if not close_response["success"]:
                logger.error(f"Failed to close positions: {close_response['error']}")
                return {
                    "statusCode": 500,
                    "body": json.dumps(close_response)
                }
        else:
            logger.info(f"No existing orders found or couldn't retrieve orders for {symbol}, proceeding with new order placement")

        # Place new order based on direction
        if direction == "LONG":
            logger.info(f"Placing buy order for {symbol}")
            order_response = place_buy_order(api_key, api_secret, symbol)
        elif direction == "SHORT":
            logger.info(f"Placing sell order for {symbol}")
            order_response = place_sell_order(api_key, api_secret, symbol)
        else:
            logger.error(f"Invalid direction received: {direction}")
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Invalid direction",
                    "details": f"Direction must be LONG or SHORT, received: {direction}"
                })
            }

        # Check if order was placed successfully
        if not order_response["success"]:
            logger.error(f"Failed to place order: {order_response['error']}")
            return {
                "statusCode": 500,
                "body": json.dumps(order_response)
            }

        # Return successful response
        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "message": f"Successfully processed {direction} signal for {symbol}",
                "order_details": order_response
            })
        }

    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal server error",
                "details": str(e)
            })
        }