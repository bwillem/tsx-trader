"""initial schema

Revision ID: initial_schema
Revises:
Create Date: 2026-01-19 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('hashed_password', sa.String(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('is_superuser', sa.Boolean(), nullable=True),
    sa.Column('questrade_access_token', sa.String(), nullable=True),
    sa.Column('questrade_refresh_token', sa.String(), nullable=True),
    sa.Column('questrade_api_server', sa.String(), nullable=True),
    sa.Column('questrade_token_expires_at', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # Create user_settings table
    op.create_table('user_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('position_size_pct', sa.Float(), nullable=True),
    sa.Column('stop_loss_pct', sa.Float(), nullable=True),
    sa.Column('daily_loss_limit_pct', sa.Float(), nullable=True),
    sa.Column('max_open_positions', sa.Integer(), nullable=True),
    sa.Column('min_cash_reserve_pct', sa.Float(), nullable=True),
    sa.Column('min_risk_reward_ratio', sa.Float(), nullable=True),
    sa.Column('paper_trading_enabled', sa.Boolean(), nullable=True),
    sa.Column('auto_trading_enabled', sa.Boolean(), nullable=True),
    sa.Column('require_stop_loss', sa.Boolean(), nullable=True),
    sa.Column('circuit_breaker_enabled', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_user_settings_id'), 'user_settings', ['id'], unique=False)

    # Create stocks table
    op.create_table('stocks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('symbol', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('exchange', sa.String(), nullable=True),
    sa.Column('sector', sa.String(), nullable=True),
    sa.Column('industry', sa.String(), nullable=True),
    sa.Column('is_active', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('symbol')
    )
    op.create_index(op.f('ix_stocks_id'), 'stocks', ['id'], unique=False)
    op.create_index(op.f('ix_stocks_symbol'), 'stocks', ['symbol'], unique=True)

    # Create market_data_daily table
    op.create_table('market_data_daily',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('stock_id', sa.Integer(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('open', sa.Float(), nullable=False),
    sa.Column('high', sa.Float(), nullable=False),
    sa.Column('low', sa.Float(), nullable=False),
    sa.Column('close', sa.Float(), nullable=False),
    sa.Column('volume', sa.Integer(), nullable=False),
    sa.Column('sma_20', sa.Float(), nullable=True),
    sa.Column('sma_50', sa.Float(), nullable=True),
    sa.Column('sma_200', sa.Float(), nullable=True),
    sa.Column('ema_12', sa.Float(), nullable=True),
    sa.Column('ema_26', sa.Float(), nullable=True),
    sa.Column('rsi_14', sa.Float(), nullable=True),
    sa.Column('macd', sa.Float(), nullable=True),
    sa.Column('macd_signal', sa.Float(), nullable=True),
    sa.Column('macd_histogram', sa.Float(), nullable=True),
    sa.Column('bollinger_upper', sa.Float(), nullable=True),
    sa.Column('bollinger_middle', sa.Float(), nullable=True),
    sa.Column('bollinger_lower', sa.Float(), nullable=True),
    sa.Column('atr_14', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['stock_id'], ['stocks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_market_data_daily_date'), 'market_data_daily', ['date'], unique=False)
    op.create_index(op.f('ix_market_data_daily_id'), 'market_data_daily', ['id'], unique=False)
    op.create_index('ix_market_data_symbol_date', 'market_data_daily', ['stock_id', 'date'], unique=False)

    # Create sentiment_posts table
    op.create_table('sentiment_posts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source', sa.String(), nullable=False),
    sa.Column('source_id', sa.String(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('author', sa.String(), nullable=True),
    sa.Column('url', sa.String(), nullable=True),
    sa.Column('published_at', sa.DateTime(), nullable=False),
    sa.Column('sentiment_compound', sa.Float(), nullable=True),
    sa.Column('sentiment_positive', sa.Float(), nullable=True),
    sa.Column('sentiment_negative', sa.Float(), nullable=True),
    sa.Column('sentiment_neutral', sa.Float(), nullable=True),
    sa.Column('upvotes', sa.Integer(), nullable=True),
    sa.Column('comments', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source_id')
    )
    op.create_index(op.f('ix_sentiment_posts_id'), 'sentiment_posts', ['id'], unique=False)
    op.create_index(op.f('ix_sentiment_posts_published_at'), 'sentiment_posts', ['published_at'], unique=False)
    op.create_index(op.f('ix_sentiment_posts_source'), 'sentiment_posts', ['source'], unique=False)

    # Create sentiment_stock_mentions table
    op.create_table('sentiment_stock_mentions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('post_id', sa.Integer(), nullable=False),
    sa.Column('stock_id', sa.Integer(), nullable=False),
    sa.Column('mention_count', sa.Integer(), nullable=True),
    sa.Column('sentiment_score', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['post_id'], ['sentiment_posts.id'], ),
    sa.ForeignKeyConstraint(['stock_id'], ['stocks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sentiment_stock_mentions_id'), 'sentiment_stock_mentions', ['id'], unique=False)
    op.create_index('ix_sentiment_post_stock', 'sentiment_stock_mentions', ['post_id', 'stock_id'], unique=False)
    op.create_index('ix_sentiment_stock_date', 'sentiment_stock_mentions', ['stock_id', 'created_at'], unique=False)

    # Create conversations table
    op.create_table('conversations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversations_id'), 'conversations', ['id'], unique=False)

    # Create messages table
    op.create_table('messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('conversation_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('tool_calls', sa.Text(), nullable=True),
    sa.Column('tool_results', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_id'), 'messages', ['id'], unique=False)
    op.create_index('ix_messages_conversation', 'messages', ['conversation_id', 'created_at'], unique=False)

    # Create positions table
    op.create_table('positions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('stock_id', sa.Integer(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('average_cost', sa.Float(), nullable=False),
    sa.Column('current_price', sa.Float(), nullable=True),
    sa.Column('market_value', sa.Float(), nullable=True),
    sa.Column('unrealized_pnl', sa.Float(), nullable=True),
    sa.Column('unrealized_pnl_pct', sa.Float(), nullable=True),
    sa.Column('realized_pnl', sa.Float(), nullable=True),
    sa.Column('stop_loss_price', sa.Float(), nullable=True),
    sa.Column('take_profit_price', sa.Float(), nullable=True),
    sa.Column('is_open', sa.Boolean(), nullable=True),
    sa.Column('opened_at', sa.DateTime(), nullable=True),
    sa.Column('closed_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['stock_id'], ['stocks.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_positions_id'), 'positions', ['id'], unique=False)
    op.create_index('ix_positions_user_stock', 'positions', ['user_id', 'stock_id'], unique=True)

    # Create portfolio_snapshots table
    op.create_table('portfolio_snapshots',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('snapshot_date', sa.Date(), nullable=False),
    sa.Column('total_value', sa.Float(), nullable=False),
    sa.Column('cash_balance', sa.Float(), nullable=False),
    sa.Column('positions_value', sa.Float(), nullable=False),
    sa.Column('daily_pnl', sa.Float(), nullable=True),
    sa.Column('daily_pnl_pct', sa.Float(), nullable=True),
    sa.Column('total_pnl', sa.Float(), nullable=True),
    sa.Column('total_pnl_pct', sa.Float(), nullable=True),
    sa.Column('num_positions', sa.Integer(), nullable=True),
    sa.Column('num_trades_today', sa.Integer(), nullable=True),
    sa.Column('win_rate', sa.Float(), nullable=True),
    sa.Column('largest_position_pct', sa.Float(), nullable=True),
    sa.Column('cash_reserve_pct', sa.Float(), nullable=True),
    sa.Column('daily_loss_from_high', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_portfolio_snapshots_id'), 'portfolio_snapshots', ['id'], unique=False)
    op.create_index(op.f('ix_portfolio_snapshots_snapshot_date'), 'portfolio_snapshots', ['snapshot_date'], unique=False)

    # Create trade_orders table
    op.create_table('trade_orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('stock_id', sa.Integer(), nullable=False),
    sa.Column('order_type', sa.Enum('MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT', name='ordertype'), nullable=False),
    sa.Column('side', sa.Enum('BUY', 'SELL', name='orderside'), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('limit_price', sa.Float(), nullable=True),
    sa.Column('stop_price', sa.Float(), nullable=True),
    sa.Column('status', sa.Enum('PENDING', 'SUBMITTED', 'PARTIAL', 'FILLED', 'CANCELLED', 'REJECTED', name='orderstatus'), nullable=False),
    sa.Column('broker_order_id', sa.String(), nullable=True),
    sa.Column('stop_loss_price', sa.Float(), nullable=True),
    sa.Column('take_profit_price', sa.Float(), nullable=True),
    sa.Column('position_size_pct', sa.Float(), nullable=True),
    sa.Column('risk_amount', sa.Float(), nullable=True),
    sa.Column('filled_quantity', sa.Integer(), nullable=True),
    sa.Column('average_fill_price', sa.Float(), nullable=True),
    sa.Column('submitted_at', sa.DateTime(), nullable=True),
    sa.Column('filled_at', sa.DateTime(), nullable=True),
    sa.Column('conversation_id', sa.Integer(), nullable=True),
    sa.Column('reasoning', sa.Text(), nullable=True),
    sa.Column('is_paper_trade', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
    sa.ForeignKeyConstraint(['stock_id'], ['stocks.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('broker_order_id')
    )
    op.create_index(op.f('ix_trade_orders_id'), 'trade_orders', ['id'], unique=False)
    op.create_index('ix_orders_user_status', 'trade_orders', ['user_id', 'status'], unique=False)

    # Create trade_executions table
    op.create_table('trade_executions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=False),
    sa.Column('broker_execution_id', sa.String(), nullable=True),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('price', sa.Float(), nullable=False),
    sa.Column('commission', sa.Float(), nullable=True),
    sa.Column('executed_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['trade_orders.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trade_executions_id'), 'trade_executions', ['id'], unique=False)

    # Create trading_decisions table
    op.create_table('trading_decisions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('stock_id', sa.Integer(), nullable=True),
    sa.Column('decision', sa.String(), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.Column('technical_signal', sa.String(), nullable=True),
    sa.Column('sentiment_score', sa.Float(), nullable=True),
    sa.Column('reasoning', sa.Text(), nullable=False),
    sa.Column('market_conditions', sa.Text(), nullable=True),
    sa.Column('suggested_action', sa.Text(), nullable=True),
    sa.Column('order_id', sa.Integer(), nullable=True),
    sa.Column('action_taken', sa.Boolean(), nullable=True),
    sa.Column('action_reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['trade_orders.id'], ),
    sa.ForeignKeyConstraint(['stock_id'], ['stocks.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trading_decisions_id'), 'trading_decisions', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_trading_decisions_id'), table_name='trading_decisions')
    op.drop_table('trading_decisions')
    op.drop_index(op.f('ix_trade_executions_id'), table_name='trade_executions')
    op.drop_table('trade_executions')
    op.drop_index('ix_orders_user_status', table_name='trade_orders')
    op.drop_index(op.f('ix_trade_orders_id'), table_name='trade_orders')
    op.drop_table('trade_orders')
    op.drop_index(op.f('ix_portfolio_snapshots_snapshot_date'), table_name='portfolio_snapshots')
    op.drop_index(op.f('ix_portfolio_snapshots_id'), table_name='portfolio_snapshots')
    op.drop_table('portfolio_snapshots')
    op.drop_index('ix_positions_user_stock', table_name='positions')
    op.drop_index(op.f('ix_positions_id'), table_name='positions')
    op.drop_table('positions')
    op.drop_index('ix_messages_conversation', table_name='messages')
    op.drop_index(op.f('ix_messages_id'), table_name='messages')
    op.drop_table('messages')
    op.drop_index(op.f('ix_conversations_id'), table_name='conversations')
    op.drop_table('conversations')
    op.drop_index('ix_sentiment_stock_date', table_name='sentiment_stock_mentions')
    op.drop_index('ix_sentiment_post_stock', table_name='sentiment_stock_mentions')
    op.drop_index(op.f('ix_sentiment_stock_mentions_id'), table_name='sentiment_stock_mentions')
    op.drop_table('sentiment_stock_mentions')
    op.drop_index(op.f('ix_sentiment_posts_source'), table_name='sentiment_posts')
    op.drop_index(op.f('ix_sentiment_posts_published_at'), table_name='sentiment_posts')
    op.drop_index(op.f('ix_sentiment_posts_id'), table_name='sentiment_posts')
    op.drop_table('sentiment_posts')
    op.drop_index('ix_market_data_symbol_date', table_name='market_data_daily')
    op.drop_index(op.f('ix_market_data_daily_id'), table_name='market_data_daily')
    op.drop_index(op.f('ix_market_data_daily_date'), table_name='market_data_daily')
    op.drop_table('market_data_daily')
    op.drop_index(op.f('ix_stocks_symbol'), table_name='stocks')
    op.drop_index(op.f('ix_stocks_id'), table_name='stocks')
    op.drop_table('stocks')
    op.drop_index(op.f('ix_user_settings_id'), table_name='user_settings')
    op.drop_table('user_settings')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
