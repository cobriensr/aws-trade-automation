# AWS Automated Trading System

## Overview

This project implements an automated trading system that executes trades based on TradingView alerts using the Tradovate API. The system uses a trend-following strategy with intelligent entry and exit management, implemented through a serverless architecture on AWS.

## Trading Strategy

### Core Components

1. Trend Validator (10-minute timeframe)
   - Primary trend direction indicator
   - Color changes trigger new trade entries
   - Blue indicates bullish trend
   - Red indicates bearish trend

2. Directional Movement Index (15-minute timeframe)
   - Manages exits and re-entries
   - DI+ and DI- crossovers signal momentum shifts
   - Used to protect profits and re-enter continuing trends

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
   - VPC-enabled for Redis access
   - Python 3.9 runtime

3. ElastiCache Redis
   - cache.t3.small instance type
   - Single node deployment
   - Used for state management
   - 2GB memory for consistent performance

4. Networking
   - Custom VPC with public/private subnets
   - NAT Gateway for Lambda internet access
   - Security groups for access control
   - Route tables for traffic management

### State Management

1. Trading State Object:

    ```python
    {
        "current_position": "NONE|LONG|SHORT",
        "trend_color": "BLUE|RED",
        "waiting_for_reentry": "YES|NO",
        "last_updated": "timestamp"
    }
    ```

2. State Transitions:
   - New Trend Signal → Clear re-entry state
   - Position Exit → Set waiting for re-entry
   - Re-entry → Clear waiting state
   - New Trade → Update position and trend color

### Alert Processing Flow

1. TradingView Alert Reception:
   - Webhook triggers API Gateway
   - Payload forwarded to Lambda
   - Initial validation performed

2. State Management:
   - Current state retrieved from Redis
   - State validation performed
   - State updates atomic through Redis

3. Trade Execution:
   - Tradovate API called for order placement
   - Order confirmation received
   - State updated based on execution

## Implementation Details

### Lambda Function

```python
async def process_webhook(event, context):
    # Parse webhook data
    webhook_data = parse_webhook_data(event)
    
    # Get current state
    trading_state = await get_trading_state()
    
    # Process based on alert type
    if webhook_data['type'] == 'trend_validator':
        await handle_trend_validator_alert(webhook_data, trading_state)
    elif webhook_data['type'] == 'di_cross':
        await handle_di_cross_alert(webhook_data, trading_state)
        
    # Execute trades if needed
    if trading_state['trade_pending']:
        await execute_trade(trading_state)
```

### State Management Functions

```python
async def handle_trend_validator_alert(data, state):
    # Clear any re-entry wait state
    state['waiting_for_reentry'] = 'NO'
    
    # Handle existing position
    if state['current_position'] != 'NONE':
        await close_position(state)
    
    # Enter new position
    state['trend_color'] = data['color']
    await enter_position(data['color'])
    
async def handle_di_cross_alert(data, state):
    if state['current_position'] != 'NONE':
        if is_valid_exit(data, state):
            await close_position(state)
            state['waiting_for_reentry'] = 'YES'
    elif state['waiting_for_reentry'] == 'YES':
        if is_valid_reentry(data, state):
            await enter_position(state['trend_color'])
            state['waiting_for_reentry'] = 'NO'
```

## Trading View Alerts Setup

### Trend Validator Alert

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

### Prerequisites

- AWS Account
- Terraform installed
- AWS CLI configured
- TradingView Pro account
- Tradovate account

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
   - Redis operations (~1ms)
   - Tradovate API (~50-100ms)

2. Optimizations:
   - Regional endpoint usage
   - Lambda in VPC
   - Connection pooling
   - Efficient state management

### Cost Optimization

Approximate monthly costs:

- Lambda: $5-10
- Redis: $25
- NAT Gateway: $32
- API Gateway: $3.50-7
- Total: $65-75

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
  