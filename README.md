# SafeOrder PakShield

SafeOrder PakShield is a Flask-based seller protection platform designed to help online sellers identify risky COD customers, manage delivery issue reports, review courier performance, and receive parcel risk alerts.

The platform helps sellers reduce unnecessary return losses by checking customer phone numbers against reported delivery issues and maintaining a centralized record of risky COD behavior.

## Problem Statement

Online sellers often face losses because of failed COD deliveries, fake orders, repeated returns, and customers who refuse parcels after shipment. Many sellers do not have a proper system to check whether a customer has a previous history of delivery issues.

Because of this, sellers may repeatedly ship orders to risky customers and face extra courier charges, return costs, and time loss.

## Solution

SafeOrder PakShield provides a digital platform where sellers can:

* Check customer phone numbers before dispatching COD orders
* Report delivery issues and risky customers
* Review courier performance
* Maintain approved customer risk records
* Track search logs and platform activity
* Receive alerts from PostEx webhook status updates
* Manage users, reports, and platform data through an admin dashboard

## Features

* Google OAuth login
* Role-based access for admin and users
* Admin dashboard
* COD customer risk checking
* Phone number normalization for accurate searching
* Delivery issue reporting
* Courier review system
* Search log tracking
* PostEx webhook integration
* Parcel risk alert generation
* Supabase database integration
* Admin approval/rejection for reports
* User management
* Clean Flask template-based interface

## Tech Stack

* Python
* Flask
* HTML
* CSS
* Jinja Templates
* Supabase
* PostgreSQL
* Authlib
* Google OAuth
* Python Dotenv
* PostEx Webhook Integration
* Visual Studio Code

## Main Modules

### Authentication

The app supports Google OAuth login. Only approved users available in the users table can access the dashboard.

### Dashboard

The dashboard shows useful platform data such as reports, users, courier reviews, searches, and alerts. Admin users can view platform-level statistics, while normal users can access their allowed features.

### COD Risk Check

Users can search a customer's phone number before dispatching an order. The system normalizes phone numbers and checks if the customer has approved delivery issue reports.

Risk levels are calculated based on the number of matching reports:

* No Issue Found
* Low Risk
* Medium Risk
* High Risk

### Delivery Issue Reporting

Users can submit delivery issue reports by adding customer phone number, customer name, city, reason, and reporter details.

### Courier Reviews

Users can submit courier reviews with courier name, city, rating, and review details. This helps sellers compare courier performance.

### Admin Panel

Admins can:

* Add users
* View total reports
* Approve reports
* Reject reports
* Delete reports
* View pending reports
* Manage platform activity

### PostEx Webhook

The app includes a PostEx webhook endpoint to receive parcel status updates. Risky parcel statuses can automatically create alert logs so sellers can take action quickly.

### Alert System

The system creates parcel risk alerts when a risky delivery status is received through the webhook.

## Project Structure

```bash
safeorder/
│
├── static/
│   └── css/
│       └── style.css
│
├── templates/
│   ├── add.html
│   ├── admin.html
│   ├── base.html
│   ├── courier_reviews.html
│   ├── dashboard.html
│   ├── index.html
│   └── login.html
│
├── app.py
├── requirements.txt
├── SHEET_SETUP.md
├── .gitignore
└── README.md
```

## Installation and Setup

Clone the repository:

```bash
git clone https://github.com/eshaa48/safeorder-pakshield.git
```

Go to the project folder:

```bash
cd safeorder-pakshield
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate the virtual environment:

For Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the Flask app:

```bash
python app.py
```

Open the app in your browser:

```text
http://127.0.0.1:5000
```

## Environment Variables

Create a `.env` file in the root folder and add the required environment variables:

```env
FLASK_SECRET_KEY=your_flask_secret_key

GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_key

POSTEX_WEBHOOK_SECRET=your_postex_webhook_secret
```

The `.env` file is not included in this repository for security reasons.

## Database Tables

This project uses Supabase tables for storing users, reports, courier reviews, search logs, webhook logs, and alert logs.

Main tables include:

* users
* bad_customers
* courier_reviews
* search_logs
* postex_webhook_logs
* alert_logs

## Security Note

Do not upload the following files to GitHub:

```text
.env
credentials.json
venv/
__pycache__/
ngrok.exe
```

These files may contain private keys, API credentials, local environment settings, or unnecessary local files.

## Future Enhancements

* Advanced search filters
* Seller subscription plans
* Daily search limits
* Business profile management
* Courier performance analytics
* Email/SMS alerts
* Admin analytics dashboard
* Multi-language support
* Public risk API for sellers
* Mobile app version

## Author

Developed by Eshaa

## Repository

GitHub: https://github.com/eshaa48/safeorder-pakshield
