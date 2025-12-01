/**
 * How It Works Modal Component for Botija Crypto
 * Contains all documentation content for the trading bot
 */

function howItWorksModal() {
  return {
    getTabHTML(tab) {
      const tabs = {
        strategy: `
          <h3 class="text-lg font-semibold text-white">What Does Botija Crypto Do?</h3>
          <p><strong class="text-green-400">Botija Crypto</strong> is an automated trading bot that buys and sells Bitcoin (BTC) for US Dollars (USD) on the Kraken exchange.</p>
          <h4 class="text-md font-semibold text-white mt-4">How It Works:</h4>
          <ul class="list-disc list-inside space-y-2 ml-2">
            <li>Analyzes the market <strong>every 4 hours</strong> (6 times per day)</li>
            <li>Uses technical indicators to detect trends and momentum</li>
            <li>Buys when the market shows strength (uptrend confirmed)</li>
            <li>Sells when momentum fades or risk increases</li>
          </ul>
          <h4 class="text-md font-semibold text-white mt-4">Key Concepts:</h4>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mt-2">
            <div class="bg-gray-800 rounded-lg p-3 border border-gray-700">
              <div class="font-semibold text-amber-400">EMA (20, 50, 200)</div>
              <div class="text-sm text-gray-400">Moving averages that show trend direction. Price above EMAs = bullish, below = bearish.</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-3 border border-gray-700">
              <div class="font-semibold text-purple-400">RSI (0-100)</div>
              <div class="text-sm text-gray-400">Momentum indicator. Below 30 = oversold (buy opportunity), above 70 = overbought (sell signal).</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-3 border border-gray-700">
              <div class="font-semibold text-blue-400">Winter Mode ❄️</div>
              <div class="text-sm text-gray-400">Safety feature that blocks trades during risky market conditions (BEAR or LATERAL regimes).</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-3 border border-gray-700">
              <div class="font-semibold text-green-400">Swing Trading</div>
              <div class="text-sm text-gray-400">Holds positions for days or weeks, capturing medium-term price movements rather than quick trades.</div>
            </div>
          </div>`,

        ai: `
          <h3 class="text-lg font-semibold text-white">The Brain Behind Decisions</h3>
          <p>Every 4 hours, the bot sends market data to <strong class="text-blue-400">GPT-5.1</strong> (OpenAI's latest AI model) which analyzes:</p>
          <ul class="list-disc list-inside space-y-1 ml-2">
            <li>Current price vs historical moving averages</li>
            <li>Momentum strength and trend direction</li>
            <li>Market volatility and risk levels</li>
            <li>RSI for overbought/oversold conditions</li>
          </ul>
          <h4 class="text-md font-semibold text-white mt-4">Market Regimes:</h4>
          <div class="space-y-2 mt-2">
            <div class="flex items-center gap-3 bg-emerald-900/20 rounded-lg p-3 border border-emerald-800/50">
              <span class="text-2xl">🟢</span>
              <div>
                <div class="font-semibold text-emerald-400">BULL</div>
                <div class="text-sm text-gray-400">Uptrend detected → Trading is <strong>allowed</strong>. Bot may buy or hold.</div>
              </div>
            </div>
            <div class="flex items-center gap-3 bg-red-900/20 rounded-lg p-3 border border-red-800/50">
              <span class="text-2xl">🔴</span>
              <div>
                <div class="font-semibold text-red-400">BEAR</div>
                <div class="text-sm text-gray-400">Downtrend detected → Trading is <strong>blocked</strong>. Winter Mode protects capital.</div>
              </div>
            </div>
            <div class="flex items-center gap-3 bg-yellow-900/20 rounded-lg p-3 border border-yellow-800/50">
              <span class="text-2xl">🟡</span>
              <div>
                <div class="font-semibold text-yellow-400">LATERAL</div>
                <div class="text-sm text-gray-400">No clear trend → Trading is <strong>blocked</strong>. Waiting for direction.</div>
              </div>
            </div>
          </div>
          <div class="bg-gray-800 rounded-lg p-4 border border-gray-700 mt-4">
            <div class="text-sm text-gray-400">
              <i class="fa-solid fa-lightbulb text-yellow-400 mr-1"></i>
              <strong>Why AI?</strong> Traditional bots use rigid rules. Our AI adapts to changing market conditions, providing context-aware analysis that considers multiple factors simultaneously.
            </div>
          </div>`,

        backtest: `
          <h3 class="text-lg font-semibold text-white">Proof It Works</h3>
          <p>We tested this strategy using <strong>real historical data</strong> to see how it would have performed before risking real money.</p>
          <h4 class="text-md font-semibold text-white mt-4">Results (January - November 2024):</h4>
          <div class="overflow-x-auto mt-2">
            <table class="w-full text-sm">
              <thead class="bg-gray-800">
                <tr>
                  <th class="px-4 py-2 text-left text-gray-400">Metric</th>
                  <th class="px-4 py-2 text-left text-gray-400">Value</th>
                  <th class="px-4 py-2 text-left text-gray-400">What It Means</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-700">
                <tr><td class="px-4 py-2 font-medium text-green-400">Total Return</td><td class="px-4 py-2 text-white">+48.7%</td><td class="px-4 py-2 text-gray-400">Bot gained 48.7% on initial investment</td></tr>
                <tr><td class="px-4 py-2 font-medium text-amber-400">BTC Buy & Hold</td><td class="px-4 py-2 text-white">+47.2%</td><td class="px-4 py-2 text-gray-400">Just holding BTC would have gained 47.2%</td></tr>
                <tr><td class="px-4 py-2 font-medium text-blue-400">Win Rate</td><td class="px-4 py-2 text-white">62%</td><td class="px-4 py-2 text-gray-400">62% of trades were profitable</td></tr>
                <tr><td class="px-4 py-2 font-medium text-purple-400">Total Trades</td><td class="px-4 py-2 text-white">23</td><td class="px-4 py-2 text-gray-400">Made 23 buy/sell operations in 11 months</td></tr>
                <tr><td class="px-4 py-2 font-medium text-red-400">Max Drawdown</td><td class="px-4 py-2 text-white">-12.3%</td><td class="px-4 py-2 text-gray-400">Largest temporary loss was 12.3%</td></tr>
                <tr><td class="px-4 py-2 font-medium text-gray-300">Avg Hold Time</td><td class="px-4 py-2 text-white">5.2 days</td><td class="px-4 py-2 text-gray-400">Held positions ~5 days on average</td></tr>
              </tbody>
            </table>
          </div>
          <div class="bg-gray-800 rounded-lg p-4 border border-gray-700 mt-4">
            <div class="text-sm text-gray-400">
              <i class="fa-solid fa-chart-pie text-green-400 mr-1"></i>
              <strong>Bottom Line:</strong> The bot slightly outperformed simply holding Bitcoin, while reducing risk through active management and avoiding major drawdowns during bearish periods.
            </div>
          </div>
          <div class="bg-yellow-900/20 rounded-lg p-4 border border-yellow-800/50 mt-2">
            <div class="text-sm text-yellow-300">
              <i class="fa-solid fa-triangle-exclamation mr-1"></i>
              <strong>Disclaimer:</strong> Past performance does not guarantee future results. Cryptocurrency trading involves significant risk.
            </div>
          </div>`,

        dashboard: `
          <h3 class="text-lg font-semibold text-white">Understanding Your Dashboard</h3>
          <h4 class="text-md font-semibold text-white mt-4"><i class="fa-solid fa-square text-gray-600 mr-1"></i> Status Cards (Top Row)</h4>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div class="bg-gray-800 rounded-lg p-3 border border-gray-700">
              <div class="font-semibold text-green-400">Bot Status</div>
              <div class="text-sm text-gray-400">Shows ACTIVE (running) or INACTIVE. Also displays trading mode: PAPER (simulated) or REAL (live money).</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-3 border border-gray-700">
              <div class="font-semibold text-amber-400">BTC Balance</div>
              <div class="text-sm text-gray-400">Amount of Bitcoin you currently hold. Shows 0 when fully in USD.</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-3 border border-gray-700">
              <div class="font-semibold text-emerald-400">USD Balance</div>
              <div class="text-sm text-gray-400">Cash available to buy Bitcoin. This is your "dry powder".</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-3 border border-gray-700">
              <div class="font-semibold text-purple-400">Total Value</div>
              <div class="text-sm text-gray-400">Your complete portfolio value in USD (BTC value + USD balance).</div>
            </div>
          </div>
          <h4 class="text-md font-semibold text-white mt-4"><i class="fa-solid fa-table text-gray-600 mr-1"></i> Trading Cycles Table</h4>
          <div class="space-y-2">
            <div class="bg-gray-800 rounded-lg p-3 border border-gray-700">
              <div class="grid grid-cols-3 gap-2 text-sm">
                <div><span class="text-gray-400">Time:</span> When the cycle executed</div>
                <div><span class="text-gray-400">Price:</span> BTC price at that moment</div>
                <div><span class="text-gray-400">Strategy:</span> Market regime + Winter Mode</div>
              </div>
            </div>
            <div class="bg-gray-800 rounded-lg p-3 border border-gray-700">
              <div class="grid grid-cols-3 gap-2 text-sm">
                <div><span class="text-gray-400">Indicators:</span> EMA20, EMA50, EMA200, RSI</div>
                <div><span class="text-gray-400">AI Signal:</span> HOLD/BUY/SELL + reasoning</div>
                <div><span class="text-gray-400">Action:</span> What the bot did</div>
              </div>
            </div>
          </div>
          <h4 class="text-md font-semibold text-white mt-4"><i class="fa-solid fa-arrows-rotate text-gray-600 mr-1"></i> Controls</h4>
          <div class="bg-gray-800 rounded-lg p-3 border border-gray-700">
            <ul class="text-sm space-y-1">
              <li><span class="text-blue-400 font-medium">Run:</span> Manually trigger a trading cycle</li>
              <li><span class="text-blue-400 font-medium">Refresh:</span> Update the table with latest data</li>
              <li><span class="text-blue-400 font-medium">Next cycle in:</span> Countdown to next analysis</li>
            </ul>
          </div>
          <h4 class="text-md font-semibold text-white mt-4"><i class="fa-solid fa-terminal text-gray-600 mr-1"></i> Application Logs</h4>
          <div class="bg-gray-800 rounded-lg p-3 border border-gray-700 text-sm text-gray-400">
            Real-time server logs. Filter by level (INFO, WARNING, ERROR) and download for debugging.
          </div>`,

        tech: `
          <h3 class="text-lg font-semibold text-white">Technology Stack</h3>
          <p class="text-gray-400">For developers and the technically curious.</p>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <div class="flex items-center gap-2 mb-2">
                <i class="fa-brands fa-python text-yellow-400 text-xl"></i>
                <span class="font-semibold text-white">Backend</span>
              </div>
              <ul class="text-sm text-gray-400 space-y-1">
                <li>• FastAPI (Python) - REST API</li>
                <li>• SQLAlchemy + SQLite - Database</li>
                <li>• APScheduler - 4h automation</li>
                <li>• Pydantic - Validation</li>
              </ul>
            </div>
            <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <div class="flex items-center gap-2 mb-2">
                <i class="fa-brands fa-js text-yellow-300 text-xl"></i>
                <span class="font-semibold text-white">Frontend</span>
              </div>
              <ul class="text-sm text-gray-400 space-y-1">
                <li>• Alpine.js - Reactive UI</li>
                <li>• TailwindCSS - Styling</li>
                <li>• No build step required</li>
                <li>• Font Awesome - Icons</li>
              </ul>
            </div>
            <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <div class="flex items-center gap-2 mb-2">
                <i class="fa-solid fa-coins text-blue-400 text-xl"></i>
                <span class="font-semibold text-white">Trading</span>
              </div>
              <ul class="text-sm text-gray-400 space-y-1">
                <li>• Kraken Exchange</li>
                <li>• CCXT Library</li>
                <li>• TA (indicators)</li>
                <li>• Pandas</li>
              </ul>
            </div>
            <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <div class="flex items-center gap-2 mb-2">
                <i class="fa-solid fa-brain text-purple-400 text-xl"></i>
                <span class="font-semibold text-white">AI & Hosting</span>
              </div>
              <ul class="text-sm text-gray-400 space-y-1">
                <li>• OpenAI GPT-5.1</li>
                <li>• Ubuntu VPS</li>
                <li>• Nginx + SSL</li>
                <li>• Systemd</li>
              </ul>
            </div>
          </div>
          <div class="bg-gray-800 rounded-lg p-4 border border-gray-700 mt-4">
            <div class="flex items-center gap-2 mb-2">
              <i class="fa-brands fa-github text-white text-xl"></i>
              <span class="font-semibold text-white">Open Source</span>
            </div>
            <p class="text-sm text-gray-400">MIT License. Contributions welcome!</p>
          </div>`
      };
      return tabs[tab] || '';
    }
  };
}

window.howItWorksModal = howItWorksModal;
