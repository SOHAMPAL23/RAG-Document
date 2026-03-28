import React from 'react';

const tickers = [
  { symbol: 'AAPL', change: '+1.24%', up: true },
  { symbol: 'MSFT', change: '+0.87%', up: true },
  { symbol: 'GOOGL', change: '-0.31%', up: false },
  { symbol: 'AMZN', change: '+2.15%', up: true },
  { symbol: 'TSLA', change: '+3.42%', up: true },
  { symbol: 'BRK.B', change: '+0.55%', up: true },
  { symbol: 'JPM', change: '+0.93%', up: true },
  { symbol: 'GS', change: '-0.17%', up: false },
  { symbol: 'NVDA', change: '+4.21%', up: true },
  { symbol: 'META', change: '+1.76%', up: true },
  { symbol: 'V', change: '+0.44%', up: true },
  { symbol: 'BAC', change: '-0.28%', up: false },
];

const TickerItem = ({ symbol, change, up }) => (
  <span className="inline-flex items-center gap-1.5 px-3">
    <span className="text-gray-500 font-semibold">{symbol}</span>
    <span className={`font-mono font-semibold ${up ? 'text-accent' : 'text-red-400'}`}>
      {up ? '▲' : '▼'}{change}
    </span>
  </span>
);

const Ticker = () => {
  return (
    <div className="w-full bg-black/30 border-b border-white/5 overflow-hidden h-7 flex items-center text-[10px] whitespace-nowrap select-none">
      <div className="animate-ticker flex">
        {[...tickers, ...tickers].map((t, i) => (
          <TickerItem key={i} {...t} />
        ))}
      </div>
    </div>
  );
};

export default Ticker;
