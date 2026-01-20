# Quick Start - GitHub Actions Deployment

Get your TSX trading analysis system running in the cloud in ~10 minutes.

## Prerequisites

✅ You already have:
- Neon database (Postgres)
- Upstash Redis
- Claude API key
- Alpha Vantage API key
- Reddit API credentials
- GitHub repository
- All secrets configured in GitHub

## Step 1: Push Code to GitHub

```bash
cd tsx-trader

# Initialize git
git init
git add .
git commit -m "Initial commit"

# Add your remote
git remote add origin https://github.com/YOUR_USERNAME/tsx-trader.git

# Push
git push -u origin main
```

## Step 2: Run Database Setup

Go to your GitHub repository:

1. Click **Actions** tab
2. Click **Database Setup** workflow
3. Click **Run workflow** dropdown
4. Select action: **full-setup**
5. Click **Run workflow** button

Wait ~2 minutes. Check that it completes successfully (green checkmark).

## Step 3: Verify Setup

Check that tables were created:

**Option A**: GitHub Actions logs
- Click on the completed workflow run
- Expand "Verify migration" step
- Should show: "Users table exists: True"

**Option B**: Neon SQL Editor
```sql
SELECT COUNT(*) FROM stocks;
-- Should return ~10 (sample TSX stocks)

SELECT COUNT(*) FROM users;
-- Should return 0 (no users yet)
```

## Step 4: Create User Account

You need at least one user for analysis to run.

**Option A**: Via API locally
```bash
# Create .env with cloud database URL
cat > .env << EOF
DATABASE_URL=your-neon-url
SECRET_KEY=your-secret-key
EOF

# Start backend
docker-compose up backend

# Register user (in another terminal)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"your-password"}'
```

**Option B**: Direct SQL (Neon dashboard)
```sql
-- Insert user with hashed password
-- Password: 'changeme' (change this!)
INSERT INTO users (email, hashed_password, is_active, created_at, updated_at)
VALUES (
  'your@email.com',
  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU2CWRqKS.Sm',
  true,
  NOW(),
  NOW()
);

-- Create user settings
INSERT INTO user_settings (
  user_id, position_size_pct, stop_loss_pct, daily_loss_limit_pct,
  max_open_positions, min_cash_reserve_pct, min_risk_reward_ratio,
  paper_trading_enabled, auto_trading_enabled, require_stop_loss,
  circuit_breaker_enabled, created_at, updated_at
)
SELECT
  id, 20.0, 5.0, 5.0, 10, 10.0, 2.0, true, true, true, true, NOW(), NOW()
FROM users WHERE email = 'your@email.com';
```

## Step 5: Enable Auto-Trading Analysis

Even though we're in analysis-only mode, you need to enable "auto trading" for scheduled analysis to run:

```sql
UPDATE user_settings
SET auto_trading_enabled = true
WHERE user_id = (SELECT id FROM users WHERE email = 'your@email.com');
```

## Step 6: Test Manual Run

Test that everything works:

1. Go to **Actions** → **Scheduled Trading Analysis**
2. Click **Run workflow**
3. Select task: **trading-analysis**
4. Click **Run workflow**

Wait ~1-2 minutes for completion.

## Step 7: Check Recommendations

After the workflow completes, check for recommendations:

**Quick way** (Python script):
```bash
export DATABASE_URL='your-neon-connection-string'
python scripts/check_recommendations.py
```

**SQL way** (Neon dashboard):
```sql
SELECT
    s.symbol,
    td.decision,
    td.confidence,
    td.reasoning,
    td.suggested_action,
    td.created_at
FROM trading_decisions td
JOIN stocks s ON td.stock_id = s.id
ORDER BY td.created_at DESC
LIMIT 5;
```

## Done! 🎉

Your system is now fully operational:

✅ **Scheduled tasks** run automatically:
- 9:30 AM EST: Morning analysis
- 4:00 PM EST: Closing analysis
- Every 30 min: Sentiment updates
- Every hour: Market data updates

✅ **Cloud-based**: Runs without your laptop

✅ **Free**: $0 infrastructure (only Claude API ~$3-6/month)

✅ **Compliant**: Analysis-only mode (Questrade compatible)

## Daily Workflow

### Morning (after 9:30 AM EST)

1. **Check GitHub Actions**: Did morning analysis run?
2. **View recommendations**:
   ```bash
   export DATABASE_URL='your-neon-url'
   python scripts/check_recommendations.py
   ```
3. **Review Claude's reasoning**
4. **Execute in Questrade** if you agree

### Afternoon (after 4:00 PM EST)

1. Check closing analysis
2. Review new recommendations
3. Execute trades in Questrade

## Troubleshooting

### No Recommendations Generated

Check:
1. **User exists**: `SELECT * FROM users;`
2. **Auto-trading enabled**: `SELECT auto_trading_enabled FROM user_settings;`
3. **Workflow succeeded**: Check Actions tab for errors
4. **API keys valid**: Check workflow logs for errors

### Workflow Failed

1. Click on failed run
2. Expand failed step
3. Read error message
4. Common fixes:
   - **Secret missing**: Add to GitHub Settings → Secrets
   - **Database connection**: Check DATABASE_URL format
   - **Import error**: May need to update requirements.txt

### "No module named 'app'"

The GitHub Action runs in the `backend/` directory, so imports work. If running locally:
```bash
cd backend
python -c "from app.database import SessionLocal"
```

## Next Steps

1. **Monitor first week**: Let it run, check results daily
2. **Add more stocks**: Edit `scripts/init-db.py`, commit, and push
3. **Adjust risk params**: Update `user_settings` table
4. **Track performance**: Log which recommendations you followed
5. **Iterate**: Refine based on what works

## Resources

- **Full deployment guide**: [GITHUB_ACTIONS_DEPLOYMENT.md](GITHUB_ACTIONS_DEPLOYMENT.md)
- **Analysis-only mode**: [ANALYSIS_ONLY_MODE.md](ANALYSIS_ONLY_MODE.md)
- **API documentation**: Run backend locally, visit http://localhost:8000/docs

## Cost Breakdown

- Neon (Postgres): **$0** (free tier)
- Upstash (Redis): **$0** (free tier)
- GitHub Actions: **$0** (free tier)
- Alpha Vantage: **$0** (free tier)
- Reddit API: **$0** (free)
- Claude API: **~$3-6/month** (2-4 calls/day)

**Total: ~$3-6/month**

Compare to:
- Railway/Render: ~$15-20/month
- Running laptop 24/7: electricity + wear
- Professional trading software: $50-500/month

You're getting AI-powered trading analysis for the price of a coffee! ☕
