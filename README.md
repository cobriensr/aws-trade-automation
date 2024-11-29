# AWS Automated Trading System

## Overview

This project implements an automated trading system that executes trades based on TradingView alerts using the Tradovate API. The system uses a trend-following strategy with intelligent entry and exit management, implemented through a serverless architecture on AWS.

## Trading Strategy

### Core Components

1. Trade Execution (1-minute timeframe)

   - All entries and exits executed on 1-minute chart
   - Provides precise entry and exit points
   - Minimizes slippage on trade execution
   - Ensures responsive position management

2. Trend Validator (10-minute timeframe)

   - Primary trend direction indicator
   - Color changes trigger new trade entries
   - Blue indicates bullish trend
   - Red indicates bearish trend

3. Directional Movement Index (15-minute timeframe)

   - Manages exits and re-entries
   - DI+ and DI- crossovers signal momentum shifts
   - Used to protect profits and re-enter continuing trends

This multi-timeframe approach combines:

- Quick execution (1-minute)
- Trend direction (10-minute)
- Momentum confirmation (15-minute)

### Strategy Logic

1. Entry Conditions:
   - Long Entry: Trend Validator turns Blue from Red
   - Short Entry: Trend Validator turns Red from Blue
   - Entry execution is immediate upon color change

2. Exit Conditions:
   - Long Exit: DI- crosses above DI+
   - Short Exit: DI+ crosses above DI-
   - Exits protect profits when momentum shifts

3. Re-entry Conditions:
   - Re-enter Long: DI+ crosses above DI- while Trend Validator is still Blue
   - Re-enter Short: DI- crosses above DI+ while Trend Validator is still Red
   - Allows catching continuation moves in strong trends

## System Architecture

### AWS Infrastructure

1. API Gateway
   - Regional endpoint for low latency
   - Handles TradingView webhook requests
   - Basic request validation and throttling

2. Lambda Function
   - 1024MB memory for optimal performance
   - 15-second timeout for trade processing
   - Python 3.9 runtime

3. Networking
   - Custom VPC with public/private subnets
   - NAT Gateway for Lambda internet access
   - Security groups for access control
   - Route tables for traffic management

4. Parameter Store
   - Secure storage for authentication tokens
   - Manages Tradovate API credentials
   - Handles token refresh lifecycle
   - Encrypted storage for sensitive data

### Alert Processing Flow

1. TradingView Alert Reception:
   - Webhook triggers API Gateway
   - Payload forwarded to Lambda
   - Initial validation performed

2. Trade Execution:
   - Tradovate API called for order placement
   - Order confirmation received
   - State updated based on execution

## Implementation Details

## Trading View Alerts Setup

### Trend Validator Alert

The system routes trades to different brokers based on both the instrument type and exchange:

Broker Routing Rules:

OANDA: All Forex pairs (e.g., EUR_USD, GBP_JPY) with exchange = OANDA
Tradovate: All Futures contracts with their respective exchanges:

- CME: ES (S&P 500), NQ (Nasdaq), RTY (Russell)
- CBOT: YM (Dow)
- NYMEX: CL (Crude Oil), GC (Gold)

The webhook payload structure remains the same for both instrument types, with the routing logic handled by the Lambda function based on the symbol:

1. Long Entry

    ```javascript
    {
        "action": "LONG_ENTRY",
        "indicator": "Trend_Validator",
        "signal": {
            "type": "ENTRY",
            "direction": "LONG",
            "trigger": "COLOR_CHANGE_BLUE"
        },
        "market_data": {
            "symbol": "{{ticker}}",
            "exchange": "{{exchange}}",
            "timeframe": "{{interval}}",
            "timestamp": "{{time}}",
            "timenow": "{{timenow}}"
        },
        "price_data": {
            "open": "{{open}}",
            "high": "{{high}}",
            "low": "{{low}}",
            "close": "{{close}}",
            "volume": "{{volume}}"
        }
    }
    ```

2. Short Entry

    ```javascript
    {
        "action": "SHORT_ENTRY",
        "indicator": "Trend_Validator",
        "signal": {
            "type": "ENTRY",
            "direction": "SHORT",
            "trigger": "COLOR_CHANGE_RED"
        },
        "market_data": {
            "symbol": "{{ticker}}",
            "exchange": "{{exchange}}",
            "timeframe": "{{interval}}",
            "timestamp": "{{time}}",
            "timenow": "{{timenow}}"
        },
        "price_data": {
            "open": "{{open}}",
            "high": "{{high}}",
            "low": "{{low}}",
            "close": "{{close}}",
            "volume": "{{volume}}"
        }
    }
    ```

## Infrastructure Deployment

### Prerequisite Steps

- AWS Account
- Terraform installed
- AWS CLI configured
- TradingView Pro account
- Tradovate account
- Required IAM Permissions
  - Parameter Store access:

  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "ssm:GetParameter",
          "ssm:PutParameter"
        ],
        "Resource": "arn:aws:ssm:${region}:${account}:parameter/tradovate/*"
      }
    ]
  }

### Deployment Steps

1. Clone repository
2. Update variables in terraform.tfvars
3. Initialize Terraform:

    ```bash
    terraform init
    ```

4. Deploy infrastructure:

    ```bash
    terraform plan
    terraform apply
    ```

## Monitoring and Maintenance

### CloudWatch Metrics

- Lambda execution times
- Trade execution success rate
- Error rates and types
- API Gateway latency

### Alerts

- Lambda function errors
- High latency notifications
- Failed trade executions
- State management issues

### Maintenance Tasks

1. Regular Reviews:
   - Performance metrics
   - Cost optimization
   - Error patterns
   - Trade execution quality

2. Updates:
   - Lambda function code
   - Dependencies
   - Security patches
   - Infrastructure as needed

## Performance Considerations

### Latency Management

1. Components:
   - TradingView webhook delay (~100ms)
   - API Gateway processing (~10ms)
   - Lambda execution (~50-100ms)
   - Tradovate API (~50-100ms)

2. Optimizations:
   - Regional endpoint usage
   - Lambda in VPC
   - Connection pooling
   - Efficient state management

### Cost Optimization

Approximate monthly costs:

1. AWS Service Costs:
   - Lambda: $5-10 (based on ~100k invocations)
   - NAT Gateway: $32 (single AZ)
   - API Gateway: $3.50-7 (based on ~100k requests)
   - Parameter Store: Free for standard parameters
   - CloudWatch Logs: $1-2
   - Total AWS Costs: $41.50-51.00

2. External Service Costs:
   - TradingView Pro: $15-30/month
   - OANDA Account: Free (commission per trade)
   - Tradovate Account: $99/month (includes data feed)
   - Tradovate API Access: $25/month
   - Total External Costs: $139-154/month

Total Estimated Monthly Operating Costs: $181.50-204.00/month

Notes:

- Costs may vary based on trading volume
- Parameter Store standard tier is free for first 10,000 parameters
- CloudWatch costs depend on log retention and volume
- External service costs may vary based on subscription level
- Tradovate account costs can increase or decrease based on tier or lifetime plan

## Security

### Network Security

- VPC isolation
- Security groups
- Private subnets
- NAT Gateway

### Data Security

- Secrets Manager for API keys
- Encrypted state storage
- Secure API endpoints
- Limited permissions
- Parameter Store for secure credential storage
  - Automatic encryption of sensitive values
  - Token lifecycle management
  - Access controlled via IAM

### Access Control

- IAM roles and policies
- Least privilege principle
- API authentication
- Resource isolation

## Future Improvements

1. Strategy Enhancements:
   - Position sizing logic
   - Multiple timeframe analysis
   - Risk management rules
   - Performance analytics

2. Technical Improvements:
   - Multi-region failover
   - Enhanced monitoring
   - Automated testing
   - Performance optimization

## Local Development and Testing

### Prerequisites

1. Install AWS SAM CLI:

   ```bash
   brew tap aws/tap
   brew install aws-sam-cli
   ```

2. Install ngrok for webhook forwarding:

    ```bash
    brew install ngrok
   ```

3. Configure AWS credentials with Parameter Store access:

   ```bash
   aws configure
   # Ensure your credentials have ssm:GetParameter and ssm:PutParameter permissions
   ```

### Local Testing Setup

1. Create a `template.yaml` in project root

    ```yaml
    AWSTemplateFormatVersion: '2010-09-09'
    Transform: AWS::Serverless-2016-10-31
    Description: Lambda function for trading automation

    Resources:
    TradingFunction:
        Type: AWS::Serverless::Function
        Properties:
        CodeUri: ./src/lambda/trading
        Handler: tradovate_token.lambda_handler
        Runtime: python3.12
        Timeout: 30
        MemorySize: 128
        Events:
            WebhookAPI:
            Type: Api
            Properties:
                Path: /webhook
                Method: POST
        LoggingConfig:
            LogFormat: JSON
            LogGroup: "/aws/lambda/trading-function"
            RetentionInDays: 30
    ```

2. Start local API endpoint

    ```bash
    sam local start-api
    ```

3. In a separate terminal, start ngrok

    ```bash
    ngrok http 3000
    ```

4. Configure webhook forwarding:

   - Copy the ngrok URL (e.g., <https://abc123.ngrok.io/webhook>)
   - Go to webhook.site
   - Set up forwarding rules to your ngrok URL

### Testing Workflow

1. Send test webhook from TradingView:

    ```javascript
        {
        "action": "LONG_ENTRY",
        "indicator": "Trend_Validator",
        "signal": {
            "type": "ENTRY",
            "direction": "LONG",
            "trigger": "COLOR_CHANGE_BLUE"
        }
    }
    ```

2. Monitor local logs:

   - SAM CLI will show Lambda execution logs
   - webhook.site shows incoming webhook data
   - ngrok interface shows request/response details

3. Debug locally:

   - Full access to local Lambda environment
   - Real-time log viewing
   - Quick iteration on code changes

### Common Issues

1. Parameter Store Local Testing:
   - Use environment variables for local testing:

     ```bash
     export TRADOVATE_USERNAME=your_username
     export TRADOVATE_PASSWORD=your_password
     export TRADOVATE_APP_ID=your_app_id
     ```

   - Mock Parameter Store responses when needed:

     ```python
     class MockParameterStore:
         def __init__(self):
             self.parameters = {}
         
         def put_parameter(self, Name, Value, Type, Overwrite=False):
             self.parameters[Name] = Value
             
         def get_parameter(self, Name, WithDecryption=False):
             return {
                 'Parameter': {
                     'Value': self.parameters.get(Name, '')
                 }
             }
     ```

   - Parameters used in production:
     - `/tradovate/token`: Current authentication token
     - `/tradovate/token_expiry`: Token expiration timestamp

2. Connectivity:

    - Ensure ngrok is running and URL is current
    - Check webhook.site forwarding rules
    - Verify local API is running on port 3000

3. Permissions:

    - Local execution uses your AWS credentials
    - Ensure proper IAM permissions
    - Test with appropriate role assumptions
