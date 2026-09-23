# Bale Inventory Control Bot

A Python-based inventory control system designed to automate product assignment, inventory reconciliation, and variance tracking for retail operations.

## Overview

This project helps retail inventory teams organize periodic stock control operations.

The system integrates:

- Bale Bot
- Google Sheets
- Retail inventory data
- OKCS online inventory services

The bot assigns products to employees, records physical inventory results, retrieves online inventory data, and helps identify inventory discrepancies.

## Main Features

- Employee-based product assignment
- Periodic inventory control scheduling
- Product prioritization
- Physical inventory recording
- Online inventory comparison
- Inventory variance tracking
- Google Sheets integration
- Bale Bot integration
- Automated control workflow
- Configurable environment variables

## Technology Stack

- Python
- Bale Bot API
- Google Sheets API
- gspread
- Google Authentication
- Requests
- Termux
- Git & GitHub

## Architecture

```text
Employee
   │
   ▼
Bale Bot
   │
   ├── Product Assignment
   │
   ├── Physical Inventory
   │
   ▼
Google Sheets
   │
   ├── Employees
   ├── Products
   ├── Assignments
   ├── Control Days
   └── Inventory Data
   │
   ▼
Online Inventory Service
   │
   ▼
Variance Detection


Security
Sensitive credentials are not stored in the source code.
The application uses environment variables for:
BALE_TOKEN
GOOGLE_SHEET_ID
OKCS_USERNAME
OKCS_PASSWORD
Credential files and local authentication data are excluded from Git using .gitignore.
Project Structure
bale_inventory_bot/
│
├── bot.py
├── requirements.txt
├── README.md
├── .gitignore
│
└── Local-only files
    ├── google_auth/
    ├── .inventory_env
    └── okcs_test.py


Installation
Clone the repository:
git clone <YOUR_REPOSITORY_URL>
cd bale_inventory_bot
Install dependencies:
pip install -r requirements.txt
Set the required environment variables:
export BALE_TOKEN="your_bale_token"
export GOOGLE_SHEET_ID="your_google_sheet_id"
export OKCS_USERNAME="your_okcs_username"
export OKCS_PASSWORD="your_okcs_password"
Then run:
python bot.py

Environment Variables
Variable
Description
BALE_TOKEN
Bale bot authentication token
GOOGLE_SHEET_ID
Google Sheets document identifier
OKCS_USERNAME
OKCS account username
OKCS_PASSWORD
OKCS account password


Notes
This repository contains a sanitized version of the project for demonstration and portfolio purposes.
Production credentials, authentication files, store data, employee information, and other private operational data are intentionally excluded.


License
This project is provided for portfolio and educational purposes.
