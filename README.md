![Logo](https://i.imgur.com/EZD3p9r.png)

## Montage

_Photo evaluation tool for and by Wiki Loves competitions_

Round-based photo evaluation is a crucial step in the "Wiki Loves"
series of photography competitions. Montage provides a configurable
workflow that adapts to the conventions of all groups.

- [montage on Wikimedia Commons](https://commons.wikimedia.org/wiki/Commons:Montage)
- [montage on Phabricator](https://phabricator.wikimedia.org/project/view/2287/)

## Testing

`pip install tox` into your virtualenv, then `tox`.
## Local Development Setup

### 1. Recommended Environment (Windows Users)

Running the backend directly on Windows may cause dependency and environment issues.  
It is highly recommended to use **Windows Subsystem for Linux (WSL)** for a smoother setup experience.

#### Steps to install WSL:

1. Open PowerShell as Administrator and run:

```wsl --install
```


2. Install Ubuntu from the Microsoft Store  

3. Open the Ubuntu terminal and run the project inside WSL  

Tested on: Windows (WSL - Ubuntu)

### 2. OAuth Consumer Setup

To enable authentication, you must create an OAuth consumer on Meta-Wiki.

1. Go to: https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration  

2. Fill in the details:
   - **Application Name:** Montage Local Dev(example)  
   - **Callback URL:** http://localhost:5000/callback  

3. Select grants:
   - Basic identity  

**IMPORTANT:**  
Ensure the box **"This consumer is for use only by [YourUsername]" is UNCHECKED**

Otherwise, you will get:
OAuthException: Consumer is owner-only (E010)


### 3. Example Configuration

Create or update your `config.dev.yaml` file:

```yaml
oauth:
  consumer_key: "your_key_here"
  consumer_secret: "your_secret_here"
  callback_url: "http://localhost:5000/callback"
```

### 4. Troubleshooting Common Setup Issues

| Error / Issue | Root Cause | Solution |
|--------------|-----------|----------|
| OAuthException (E010) | Consumer is owner-only | Uncheck "owner-only" in Meta-Wiki |
| Invalid Consumer | Incorrect key/secret | Verify credentials carefully |
| Callback issues | URL mismatch | Ensure callback URL matches exactly |
| Dependency errors | Running on Windows | Use WSL (Ubuntu) |