"""Manage CloudWatch metrics for Tradovate trading operations."""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()

class TradovateMetricsManager:
    """Manages CloudWatch metrics for Tradovate operations with better data consistency."""
    
    def __init__(self, namespace: str = "Trading/Webhook"):
        """Initialize the metrics manager with CloudWatch client."""
        self.cloudwatch = boto3.client('cloudwatch')
        self.namespace = namespace
        self.default_dimensions = []
        
    def set_default_dimensions(self, dimensions: list) -> None:
        """Set default dimensions for all metrics."""
        self.default_dimensions = dimensions
        
    def publish_metric_with_zero(self, metric_name: str, actual_value: float = 1, unit: str = "Count", dimensions: list = None) -> None:
        """
        Publish a metric with both actual value and zero values to prevent insufficient data.
        This helps maintain continuous data points even during periods of inactivity.
        """
        try:
            now = datetime.now(timezone.utc)
            
            # Combine default and metric-specific dimensions
            all_dimensions = self.default_dimensions.copy()
            if dimensions:
                all_dimensions.extend(dimensions)
                
            # Prepare metric data with both actual value and zero
            metric_data = [
                {
                    "MetricName": metric_name,
                    "Value": actual_value,
                    "Unit": unit,
                    "Timestamp": now,
                    "Dimensions": all_dimensions
                },
                {
                    "MetricName": f"{metric_name}_baseline",
                    "Value": 0,
                    "Unit": unit,
                    "Timestamp": now,
                    "Dimensions": all_dimensions
                }
            ]
            
            # Publish metrics
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=metric_data
            )
            
            logger.debug(f"Successfully published metric {metric_name} with value {actual_value}")
            
        except ClientError as e:
            logger.error(f"Failed to publish metric {metric_name}: {str(e)}")
            
    def publish_operation_metrics(self, operation_name: str, duration: float, success: bool, additional_data: Dict[str, Any] = None) -> None:
        """
        Publish a complete set of metrics for an operation including duration, success rate,
        and any additional custom metrics.
        """
        try:
            dimensions = [
                {'Name': 'Operation', 'Value': operation_name}
            ]
            
            # Publish standard metrics
            self.publish_metric_with_zero(
                'OperationDuration',
                duration,
                'Milliseconds',
                dimensions
            )
            
            self.publish_metric_with_zero(
                'OperationSuccess',
                1 if success else 0,
                'Count',
                dimensions
            )
            
            # Publish additional custom metrics if provided
            if additional_data:
                for metric_name, value in additional_data.items():
                    if isinstance(value, (int, float)):
                        self.publish_metric_with_zero(
                            metric_name,
                            value,
                            'Count',
                            dimensions
                        )
                        
        except Exception as e:
            logger.error(f"Failed to publish operation metrics: {str(e)}")
            
    def create_alarm(self, metric_name: str, threshold: float, evaluation_periods: int = 5, period: int = 300) -> Optional[str]:
        """
        Create or update a CloudWatch alarm for a metric with appropriate baseline monitoring.
        """
        try:
            alarm_name = f"{self.namespace}-{metric_name}-Alert"
            
            self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                MetricName=metric_name,
                Namespace=self.namespace,
                Statistic='Average',
                Period=period,
                EvaluationPeriods=evaluation_periods,
                Threshold=threshold,
                ComparisonOperator='GreaterThanThreshold',
                TreatMissingData='notBreaching',
                ActionsEnabled=True,
                AlarmDescription=f'Alert for {metric_name} exceeding {threshold}',
                Dimensions=self.default_dimensions
            )
            
            logger.info(f"Successfully created/updated alarm: {alarm_name}")
            return alarm_name
            
        except ClientError as e:
            logger.error(f"Failed to create alarm for {metric_name}: {str(e)}")
            return None