from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume, RSI, SimpleMovingAverage

 
def initialize(context):
    set_long_only()
    set_commission(commission.PerTrade(cost=0))
            
    attach_pipeline(make_pipeline(), 'my_pipeline')
    context.paid = 0
    context.shares = 0
    context.stop_value = 0
    
    context.stop_percent = .97 # Stop percentage of purchase price
    context.stop_margin = 0.01 # Stop increment margin (percentage of purchase price)
    context.stock_drawdown = 0.05 # Stock percentage drawdown
    context.purchase_percent = .75 # Percentage of portfolio to invest
    context.account_buffer = 10000 # Amount of cash to leave in account as buffer
    
    schedule_function(
        buy_losers,
        date_rules.every_day(),
        time_rules.market_open(hours=0, minutes=5))
    
#    schedule_function(
#        close_month,
#        date_rules.month_end(),
#        time_rules.market_close(hours=0, minutes=30))        
    
    schedule_function(
        record_vars,
        date_rules.every_day())
         
def make_pipeline():
    
    pipe=Pipeline()
     
    # Create factors
    price = SimpleMovingAverage(inputs=[USEquityPricing.close], window_length=22)
    volume = SimpleMovingAverage(inputs=[USEquityPricing.volume], window_length=22)
    rsi = RSI(window_length = 5)
    
    price_filter  = (price >= 5.00)
    volume_filter = (volume >= 5000000)
    rsi_filter = (rsi <= 20)

    pipe.set_screen(price_filter & volume_filter & rsi_filter)
    
    pipe = Pipeline(
        screen = price_filter & volume_filter & rsi_filter, 
        columns = {
            'price': price,
            'volume': volume,
            'rsi': rsi
        }
    )
    return pipe
 
   
def before_trading_start(context, data):
    
    context.output = pipeline_output('my_pipeline')
    print "%d securities cleared the screener" % len(context.output)
    
    context.security_list = context.output.index
    print "%d securities owned" % len(context.portfolio.positions)
    
                          
        
def buy_losers(context, data):
    if not get_open_orders():
        
        for stock in context.security_list:    
            previous_close_data = data.history(stock,'price',4,'1d')
            previous_close = previous_close_data[-1]
            pre_previous_close = previous_close_data[-2]
            context.loss = (pre_previous_close - previous_close) / pre_previous_close
        
            if (data.can_trade(stock) and 
                context.loss > context.stock_drawdown and
                context.portfolio.cash >= context.account_buffer
                ):
            
                order_target_value(stock, (context.purchase_percent * context.portfolio.cash)/len(context.output))
                context.stop_value = (context.stop_percent * context.paid)
                print "*** PURCHASED %s ***" % stock
                
            else:
                pass
    else:
        pass
     
def assign_weights(context, data):
    
    pass
 
def record_vars(context, data):
    record(Cash = context.portfolio.cash,
          Invested = context.portfolio.positions_value, 
          Total = context.portfolio.portfolio_value,
          Securities = len(context.portfolio.positions)
          )

def handle_data(context,data):
    
    for stock in context.portfolio.positions:  
        context.shares = context.portfolio.positions[stock].amount
        context.paid = context.portfolio.positions[stock].cost_basis
        context.price = data.current(stock,'price') 
        
    trailing_stop(context,data)
    
    if context.portfolio.cash < 0:
        print ")*)*)*)*)*)*)*)  NEGATIVE CASH  (*(*(*(*(*(*(*("
            

def wipe_stops(context):
    # Reset stop values to 0.0 after closing position #
    context.stop_value = 0.0     
    context.stop_margin = 0.0
    

def trailing_stop(context,data):
    # If below cost basis set stop loss #
    for stock in context.portfolio.positions:
        stop_margin = (context.stop_margin * context.paid)
    
        if context.price <= context.stop_value:
            order_target_value(stock, 0)
            wipe_stops(context)
            context.stop_value = (context.stop_percent * context.paid)
            print "*** SOLD %s ***" % stock
        
    # If above cost basis, trail stop up #        
        elif context.price - context.stop_value > stop_margin and stop_margin > 0.0:
            context.stop_value = context.price - stop_margin
            
def close_month(context,data):
    for stock in context.portfolio.positions:
        order_target_value(stock, 0)
        wipe_stops(context)
        print "#### MONTH END - CLOSED ALL POSITIONS ####"
    