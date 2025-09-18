// Include the trading library to simplify trade execution
#include <Trade\Trade.mqh>

//Input parameters for different technical indicators
input int ema_length = 66;
input int rsi_length = 14;
input int adx_length = 14;
input int atr_length = 14;
input int rsi_buy_threshold = 51;
input int rsi_sell_threshold = 67;
input int adx_threshold = 22;
input int TimeStartHour = 12;
input int TimeStartMin = 0;
input int TimeEndHour = 20;
input int TimeEndMin = 0;
input int max_sl_pips = 10;
input double take_profit_multiplier = 3.1;
input double stop_loss_multiplier = 1.1;

//Create CTrade Object for executing trades
CTrade trade;

int OnInit()
  {
   Print("SUCCEED");
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   
  }

void OnTick() {
static datetime timestamp;
//Get Current Candle's Time
datetime time = iTime(_Symbol,PERIOD_CURRENT,0);

//Check if a new tick has arrived
if (timestamp != time) { 
   timestamp = time;
   MqlDateTime structTime;
   TimeCurrent(structTime); 
   structTime.sec = 0;     
   
   //Define the start time of the trading window
   structTime.hour = TimeStartHour;  
   structTime.min = TimeStartMin;    
   datetime timestart = StructToTime(structTime);  
   
   //Define the end time of the trading window
   structTime.hour = TimeEndHour;    
   structTime.min = TimeEndMin;      
   datetime timeEnd = StructToTime(structTime);  
   
   // Check if current time is within the time window
   bool isTime = TimeCurrent() >= timestart && TimeCurrent() <= timeEnd;
   if(!isTime){
      return;
   }
   
   //Get current values of indicators
   int emahandler = iMA(_Symbol, PERIOD_CURRENT,ema_length,0,MODE_EMA,PRICE_CLOSE);
   double emaArray[];
   ArraySetAsSeries(emaArray, true);
   CopyBuffer(emahandler,0,1,1,emaArray);
   
   int atrhandler = iATR(_Symbol,PERIOD_CURRENT,atr_length);
   double atrArray [];
   ArraySetAsSeries(atrArray, true);
   CopyBuffer(atrhandler,0,1,1,atrArray);
   
   int rsihandler = iRSI(_Symbol, PERIOD_CURRENT, rsi_length,PRICE_CLOSE);
   double rsiArray [];
   ArraySetAsSeries(rsiArray,true);
   CopyBuffer(rsihandler,0,1,1,rsiArray);
   
   int adxhandler = iADX(_Symbol,PERIOD_CURRENT,adx_length);
   double adxArray [];
   ArraySetAsSeries(adxArray, true);
   CopyBuffer(adxhandler,0,1,1,adxArray);
   
   // If ATR is too low or too high, do not proceed with the trade
   if (atrArray[0]*10000 <5 || atrArray[0]*10000 >10){
   return;
   }
   // Get the current Ask price
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);   
   
   //Buy Condition  
   if (ask < (emaArray[0] - 1.5 * atrArray[0]) && rsiArray[0] < rsi_buy_threshold && adxArray[0]> adx_threshold && PositionsTotal()==0){
      //Caculate Position Size
      double position_size = (0.01*10000) / (atrArray[0]*10000*10);
      position_size = NormalizeDouble(position_size, 2);//round position size to 2 decimal places to prevent errors
      
      //Caculate SL and TP 
      double sl=ask-stop_loss_multiplier*atrArray[0];
      double tp=ask+take_profit_multiplier*atrArray[0];
      trade.Buy(position_size,_Symbol,ask,sl,tp,NULL);
      
   }  
   // Get the current Bid price
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   
   //Sell Condition    
   if (bid > (emaArray[0] + 1.5 * atrArray[0]) && rsiArray[0] > rsi_sell_threshold  && adxArray[0]> adx_threshold && PositionsTotal()==0){
      //Caculate Position Size
      double position_size = (0.01*10000) / (atrArray[0]*10000*10);
      position_size = NormalizeDouble(position_size, 2);//round position size to 2 decimal places to prevent errors
      
      //Buy Condition 
      double sl=bid+stop_loss_multiplier*atrArray[0];
      double tp=bid-take_profit_multiplier*atrArray[0];
      trade.Sell(position_size,_Symbol,bid,sl,tp,NULL);
  }
 }
}








