#!/usr/bin/env python3
"""
Test Alpha Vantage API and TSX stock support

This script tests:
1. Whether API key is working
2. Whether Alpha Vantage has data for TSX stocks
3. What symbol format works (.TO suffix vs TOR: prefix)
"""

import sys
import os
import requests
import time

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings

settings = get_settings()


def test_api_key():
    """Test if API key is valid"""
    print("=" * 80)
    print("TEST 1: API Key Validation")
    print("=" * 80)

    if not settings.ALPHA_VANTAGE_API_KEY:
        print("✗ ERROR: No API key found in environment")
        print("  Set ALPHA_VANTAGE_API_KEY in .env file")
        return False

    # Mask API key for display
    masked_key = settings.ALPHA_VANTAGE_API_KEY[:8] + "..." + settings.ALPHA_VANTAGE_API_KEY[-4:]
    print(f"API Key: {masked_key}")

    # Test with a known US stock
    print("\nTesting with US stock (AAPL)...")

    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": "AAPL",
        "apikey": settings.ALPHA_VANTAGE_API_KEY
    }

    response = requests.get("https://www.alphavantage.co/query", params=params)
    data = response.json()

    if "Global Quote" in data and "05. price" in data["Global Quote"]:
        price = data["Global Quote"]["05. price"]
        print(f"✓ API key is valid! AAPL price: ${price}")
        return True
    elif "Note" in data:
        print(f"✗ Rate limit hit: {data['Note']}")
        return False
    elif "Error Message" in data:
        print(f"✗ API error: {data['Error Message']}")
        return False
    else:
        print(f"✗ Unexpected response: {data}")
        return False


def test_tsx_symbol_formats():
    """Test different TSX symbol formats"""
    print("\n" + "=" * 80)
    print("TEST 2: TSX Symbol Format Testing")
    print("=" * 80)

    # TD Bank - well-known TSX stock
    formats_to_test = [
        ("TD.TO", "Standard format"),
        ("TD.TSE", "Alternative suffix"),
        ("TOR:TD", "Prefix format"),
        ("TSE:TD", "Exchange prefix"),
    ]

    for symbol, description in formats_to_test:
        print(f"\nTesting {symbol} ({description})...")
        time.sleep(13)  # Rate limit: 5 calls per minute

        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": settings.ALPHA_VANTAGE_API_KEY
        }

        response = requests.get("https://www.alphavantage.co/query", params=params)
        data = response.json()

        if "Global Quote" in data:
            quote = data["Global Quote"]
            if "05. price" in quote and quote["05. price"]:
                price = quote["05. price"]
                print(f"✓ SUCCESS! Price: ${price}")
                print(f"  Full name: {quote.get('01. symbol', 'N/A')}")
                return symbol  # Return working format
            else:
                print(f"✗ Empty quote data")
        elif "Note" in data:
            print(f"⏸ Rate limit: {data['Note']}")
        else:
            print(f"✗ No data: {data}")

    print("\n✗ No working format found for TSX stocks")
    return None


def test_fundamental_data(symbol):
    """Test if fundamental data is available for TSX stock"""
    print("\n" + "=" * 80)
    print(f"TEST 3: Fundamental Data for {symbol}")
    print("=" * 80)

    endpoints = [
        ("OVERVIEW", "Company Overview"),
        ("INCOME_STATEMENT", "Income Statement"),
        ("BALANCE_SHEET", "Balance Sheet"),
        ("CASH_FLOW", "Cash Flow"),
    ]

    results = {}

    for function, name in endpoints:
        print(f"\nTesting {name}...")
        time.sleep(13)  # Rate limit

        params = {
            "function": function,
            "symbol": symbol,
            "apikey": settings.ALPHA_VANTAGE_API_KEY
        }

        response = requests.get("https://www.alphavantage.co/query", params=params)
        data = response.json()

        if function == "OVERVIEW":
            has_data = "Symbol" in data and data["Symbol"]
            if has_data:
                print(f"✓ Has data")
                print(f"  Company: {data.get('Name', 'N/A')}")
                print(f"  Exchange: {data.get('Exchange', 'N/A')}")
                print(f"  Market Cap: {data.get('MarketCapitalization', 'N/A')}")
            else:
                print(f"✗ No data: {data.keys()}")
        else:
            has_quarterly = "quarterlyReports" in data and len(data["quarterlyReports"]) > 0
            has_annual = "annualReports" in data and len(data["annualReports"]) > 0

            if has_quarterly or has_annual:
                print(f"✓ Has data")
                if has_quarterly:
                    print(f"  Quarterly reports: {len(data['quarterlyReports'])}")
                if has_annual:
                    print(f"  Annual reports: {len(data['annualReports'])}")
            elif "Note" in data:
                print(f"⏸ Rate limit: {data['Note']}")
            else:
                print(f"✗ No data: {data.keys()}")

        results[name] = has_data if function == "OVERVIEW" else (has_quarterly or has_annual)

    return results


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("ALPHA VANTAGE TSX COMPATIBILITY TEST")
    print("=" * 80)
    print()
    print("This script tests whether Alpha Vantage supports TSX stocks.")
    print("It will use 5+ API calls, so don't run this multiple times.")
    print()

    # Test 1: API key
    if not test_api_key():
        print("\n✗ API key test failed. Fix this first.")
        return

    # Test 2: TSX symbol formats
    print("\n⏳ Testing TSX symbol formats (takes ~1 minute)...")
    working_symbol = test_tsx_symbol_formats()

    if not working_symbol:
        print("\n" + "=" * 80)
        print("⚠️  IMPORTANT FINDING")
        print("=" * 80)
        print()
        print("Alpha Vantage may not support TSX stocks with their free API.")
        print()
        print("ALTERNATIVES:")
        print("  1. Use Alpha Vantage Premium ($50/month) - might have TSX coverage")
        print("  2. Switch to different data provider:")
        print("     • Financial Modeling Prep (has TSX, $15/month)")
        print("     • Polygon.io (has TSX, $29/month)")
        print("     • Yahoo Finance (free via yfinance library)")
        print()
        return

    # Test 3: Fundamental data
    print("\n⏳ Testing fundamental data (takes ~1 minute)...")
    results = test_fundamental_data(working_symbol)

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"\n✓ Working symbol format: {working_symbol}")
    print(f"\nFundamental data availability:")
    for name, has_data in results.items():
        status = "✓ Available" if has_data else "✗ Not available"
        print(f"  {name}: {status}")

    all_available = all(results.values())
    if all_available:
        print(f"\n✓ SUCCESS! Alpha Vantage has full fundamental data for TSX stocks.")
        print(f"  Update your symbols to use format: {working_symbol}")
    else:
        print(f"\n✗ PARTIAL: Some fundamental data is missing.")
        print(f"  This may limit screening capabilities.")


if __name__ == "__main__":
    main()
