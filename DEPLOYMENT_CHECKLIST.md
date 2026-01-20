# GitHub Actions Deployment Checklist

Use this checklist to ensure everything is configured correctly.

## Pre-Deployment

### ✅ Cloud Services

- [ ] **Neon account** created at neon.tech
- [ ] **Neon database** created
- [ ] **Connection string** copied (starts with `postgresql://`)
- [ ] **Upstash account** created at upstash.com
- [ ] **Redis database** created
- [ ] **Redis URL** copied (starts with `redis://` or `rediss://`)

### ✅ API Keys

- [ ] **Claude API key** from console.anthropic.com
- [ ] **Alpha Vantage key** from alphavantage.co (free tier)
- [ ] **Reddit app** created at reddit.com/prefs/apps
- [ ] **Reddit client ID** copied
- [ ] **Reddit client secret** copied
- [ ] **Questrade Practice Account** (optional, for testing)

### ✅ GitHub Repository

- [ ] **Repository created** on GitHub (public or private)
- [ ] **Local git** initialized
- [ ] **All code** committed locally

## GitHub Secrets Configuration

Go to: Repository → Settings → Secrets and variables → Actions → New repository secret

Add these secrets (case-sensitive):

- [ ] **DATABASE_URL**
  ```
  Example: postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/tsx_trader
  ```

- [ ] **REDIS_URL**
  ```
  Example: rediss://default:xxx@usw1-xxx.upstash.io:6379
  ```

- [ ] **CLAUDE_API_KEY**
  ```
  Example: sk-ant-api03-xxx
  ```

- [ ] **SECRET_KEY**
  ```
  Generate random string: openssl rand -hex 32
  Example: a1b2c3d4e5f6...
  ```

- [ ] **ALPHA_VANTAGE_API_KEY**
  ```
  Example: ABC123XYZ
  ```

- [ ] **REDDIT_CLIENT_ID**
  ```
  Example: abcdefg123456
  ```

- [ ] **REDDIT_CLIENT_SECRET**
  ```
  Example: xyz789-abc123
  ```

### ✅ Verify Secrets

- [ ] All 7 secrets added
- [ ] No typos in secret names
- [ ] Values don't have extra spaces or quotes

## Initial Deployment

### ✅ Push Code

```bash
cd tsx-trader
git add .
git commit -m "Initial deployment"
git push -u origin main
```

- [ ] Code pushed successfully
- [ ] No errors in terminal

### ✅ Run Database Setup

1. Go to repository → **Actions** tab
2. Select **Database Setup** workflow
3. Click **Run workflow** → Select **full-setup** → **Run workflow**

- [ ] Workflow started
- [ ] Workflow completed successfully (green checkmark)
- [ ] "Verify migration" step shows tables exist
- [ ] "Verify stocks" step shows 10 stocks

### ✅ Create User

**Option 1: SQL** (easiest for first setup)

```sql
-- In Neon SQL Editor
INSERT INTO users (email, hashed_password, is_active, created_at, updated_at)
VALUES ('your@email.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU2CWRqKS.Sm', true, NOW(), NOW());

INSERT INTO user_settings (user_id, position_size_pct, stop_loss_pct, daily_loss_limit_pct, max_open_positions, min_cash_reserve_pct, min_risk_reward_ratio, paper_trading_enabled, auto_trading_enabled, require_stop_loss, circuit_breaker_enabled, created_at, updated_at)
SELECT id, 20.0, 5.0, 5.0, 10, 10.0, 2.0, true, true, true, true, NOW(), NOW()
FROM users WHERE email = 'your@email.com';
```

- [ ] User inserted (check: `SELECT * FROM users;`)
- [ ] Settings created (check: `SELECT * FROM user_settings;`)
- [ ] `auto_trading_enabled = true`

## First Test Run

### ✅ Manual Workflow Trigger

1. Go to **Actions** → **Scheduled Trading Analysis**
2. Click **Run workflow**
3. Select task: **all**
4. Click **Run workflow**

- [ ] Workflow started
- [ ] All jobs ran (market-data, sentiment, trading-analysis)
- [ ] All jobs completed successfully

### ✅ Verify Data Collection

```sql
-- Check market data
SELECT symbol, MAX(date) as latest FROM market_data_daily GROUP BY symbol;
```
- [ ] Shows data for multiple stocks
- [ ] Dates are recent

```sql
-- Check sentiment
SELECT COUNT(*) FROM sentiment_posts WHERE created_at > NOW() - INTERVAL '1 hour';
```
- [ ] Shows some posts (might be 0 if no Reddit mentions recently)

```sql
-- Check trading decisions
SELECT * FROM trading_decisions ORDER BY created_at DESC LIMIT 3;
```
- [ ] Shows at least one decision
- [ ] Has decision, confidence, reasoning
- [ ] `suggested_action` is populated

## Verification

### ✅ Check Recommendations

**Via Python script**:
```bash
export DATABASE_URL='your-neon-url'
python scripts/check_recommendations.py
```

- [ ] Script runs without errors
- [ ] Shows recommendations
- [ ] Displays reasoning and suggested actions

**Via SQL**:
```sql
SELECT s.symbol, td.decision, td.confidence, td.created_at
FROM trading_decisions td
JOIN stocks s ON td.stock_id = s.id
ORDER BY td.created_at DESC
LIMIT 5;
```

- [ ] Returns results
- [ ] Confidence values between 0 and 1
- [ ] Recent timestamps

### ✅ Scheduled Tasks

Check the workflow schedules:

- [ ] **Actions** tab shows scheduled workflows
- [ ] Cron times are correct (9:30 AM, 4:00 PM EST = 14:30, 21:00 UTC)

Wait for next scheduled run (or wait until tomorrow):

- [ ] Morning analysis (9:30 AM EST) ran automatically
- [ ] Afternoon analysis (4:00 PM EST) ran automatically

## Production Readiness

### ✅ Monitoring Setup

- [ ] Workflow notifications enabled (Settings → Notifications)
- [ ] Email notifications for failed workflows
- [ ] GitHub mobile app installed (optional)

### ✅ Questrade Connection (Optional)

If using Questrade for portfolio monitoring:

- [ ] Questrade Practice Account created
- [ ] OAuth credentials obtained
- [ ] Connected via API (when backend running locally)

### ✅ Documentation Review

- [ ] Read [ANALYSIS_ONLY_MODE.md](ANALYSIS_ONLY_MODE.md)
- [ ] Understand manual execution workflow
- [ ] Know how to check recommendations
- [ ] Know how to execute trades in Questrade

## Daily Operations Checklist

### Morning Routine

- [ ] Check GitHub Actions (did 9:30 AM run succeed?)
- [ ] View recommendations (`python scripts/check_recommendations.py`)
- [ ] Review Claude's reasoning
- [ ] Execute trades in Questrade if you agree

### Afternoon Routine

- [ ] Check GitHub Actions (did 4:00 PM run succeed?)
- [ ] View new recommendations
- [ ] Execute trades if needed

### Weekly Review

- [ ] Review all recommendations from the week
- [ ] Calculate success rate (which suggestions worked?)
- [ ] Adjust risk parameters if needed
- [ ] Check costs (Claude API usage)

## Troubleshooting Checks

If something isn't working:

### Database Connection Issues

```sql
-- Can you connect to Neon?
SELECT 1;
```
- [ ] Connection works

### Secrets Issues

1. Go to Settings → Secrets
2. Click on each secret
3. Click "Update" to verify it's set

- [ ] All secrets show "Updated X days ago"
- [ ] No secrets show "Never used"

### Workflow Issues

- [ ] Check workflow logs for errors
- [ ] Look for red X marks in Actions tab
- [ ] Read error messages in failed steps

Common errors:
- `No module named 'app'` → Script running from wrong directory
- `Connection refused` → DATABASE_URL incorrect
- `Authentication failed` → API key invalid
- `Rate limit exceeded` → Too many API calls

## Success Criteria

You're ready for production when:

- [x] All workflows run successfully
- [x] Database contains market data and sentiment
- [x] Trading decisions are being created
- [x] You can view recommendations
- [x] Scheduled tasks run automatically
- [x] You understand the analysis-only workflow

## Cost Monitoring

Track your costs:

- **Neon**: Check dashboard for usage (should be well under free tier)
- **Upstash**: Check dashboard for command count
- **GitHub Actions**: Settings → Billing (check minutes used)
- **Claude API**: console.anthropic.com → Usage

Monthly targets:
- [ ] Neon: Under 0.5 GB (free tier limit)
- [ ] Upstash: Under 10K commands/day (free tier)
- [ ] GitHub Actions: Under 2,000 minutes (free tier)
- [ ] Claude API: ~$3-6 (2-4 calls/day)

## Notes

Date deployed: ________________

Initial user email: ________________

Neon project: ________________

Any custom configurations: ________________

---

**Status**: [ ] Not Started  [ ] In Progress  [ ] Complete  [ ] Production

**Last updated**: ________________
