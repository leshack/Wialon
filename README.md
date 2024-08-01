# Wialon Fleet Management System

## Getting Started

To get started with this project, follow these steps:

### 1. Copy `.env.example` to `.env`

First, create a copy of the `.env.example` file and name it `.env`. This file will contain your specific settings and credentials.

```sh
cp .env.example .env

```
### 2. Creat a virtual environment 

```sh
python -m venv env

```

Activate On Windows:

```sh
.\env\Scripts\activate
```

Activate On macOS and Linux:
```sh
source env/bin/activate
```

### 3. Install requirements 

```sh
pip install -r requirements.txt
```

### 4. Run the Script

```sh
python wialon.py
```
*N/B- If username on the .env defaults to user pc username kindly declare it on the wialon.py file

### Important Links of Wialon 

https://hosting.wialon.com/?lang=en
https://help.wialon.com/help/wialon-hosting/en/expert-articles/sdk/intro-to-sdk-basic-requests#IntrotoSDK\:BasicRequests-ViewingRequestsintheBrowser
https://www.postman.com/wialon/workspace/wialon/request/33385432-b1a3e175-1759-4b67-a6e2-1a9315fff46d
https://sdk.wialon.com/wiki/en/sidebar/remoteapi/remoteapi
https://hosting.wialon.com/login.html ---link to get access token at the weblink