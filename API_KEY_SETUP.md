# OpenAI API Key Setup Guide

The Coding Agent system requires an OpenAI API key to function. This guide shows you three ways to configure it.

## 🚀 Quick Start

Run the setup script for guided configuration:
```bash
python setup_api_key.py
```

## 📋 Manual Setup Options

### Option 1: Web Dashboard (Recommended)
**Secure encrypted storage with web interface**

1. Start the web dashboard:
   ```bash
   python web_dashboard.py
   ```

2. Open http://localhost:8000 in your browser

3. Click **"API Settings"** in the navigation bar

4. Enter your OpenAI API key in the form

5. Click **"Save API Key"**

**Features:**
- ✅ Encrypted storage using Fernet encryption
- ✅ Easy to update or remove
- ✅ Automatic environment variable setting
- ✅ Key validation (checks for 'sk-' prefix)

### Option 2: .env File
**Simple file-based configuration**

1. Copy the template:
   ```bash
   cp .env.template .env
   ```

2. Edit `.env` and replace `your-openai-api-key-here` with your actual key:
   ```bash
   OPENAI_API_KEY=sk-your-actual-key-here
   ```

3. The system will automatically load the key on startup

**Features:**
- ✅ Simple and familiar
- ✅ Good for development
- ✅ Automatic file permission setting (owner-only)

### Option 3: Environment Variable
**Traditional environment variable approach**

Set the environment variable before running the system:

```bash
# For current session
export OPENAI_API_KEY='sk-your-actual-key-here'

# Then run the system
python main.py
```

For permanent setup, add to your shell profile:
```bash
echo 'export OPENAI_API_KEY="sk-your-actual-key-here"' >> ~/.bashrc
# or for zsh
echo 'export OPENAI_API_KEY="sk-your-actual-key-here"' >> ~/.zshrc
```

## 🔑 Getting Your API Key

1. Go to [OpenAI Platform](https://platform.openai.com/account/api-keys)
2. Sign in to your account
3. Click **"Create new secret key"**
4. Copy the key (it starts with `sk-`)
5. Use it in any of the setup methods above

## 🔒 Security Notes

- **Web Dashboard**: Keys are encrypted using Fernet encryption and stored in `config/secure_config.json`
- **.env File**: File permissions are automatically set to owner-only (600)
- **Environment Variables**: Stored in memory only, not persisted

## 🧪 Testing Your Setup

After setting up your API key, test the system:

```bash
# Test the main system
python main.py --list-projects

# Test the web dashboard
python web_dashboard.py
# Then visit http://localhost:8000
```

You should see:
- ✅ "OpenAI API key loaded successfully" message
- ✅ Green checkmark in the API Settings page
- ✅ Ability to create and process tasks

## 🔧 Troubleshooting

### "No API key configured" message
- Check that your key starts with `sk-`
- Verify the key is correctly set in your chosen method
- Restart the application after setting the key

### "Invalid API key" error
- Verify your key is correct and active
- Check your OpenAI account has sufficient credits
- Try regenerating the key on the OpenAI platform

### Permission errors with .env file
- The system automatically sets secure permissions
- If issues persist, manually set: `chmod 600 .env`

## 🔄 Changing Your API Key

### Web Dashboard
1. Go to http://localhost:8000/api_key_settings
2. Enter your new key in the "Update API Key" section
3. Click "Update API Key"

### .env File
1. Edit the `.env` file
2. Replace the old key with the new one
3. Restart the application

### Environment Variable
1. Set the new value: `export OPENAI_API_KEY='sk-new-key-here'`
2. Restart the application

## 🗑️ Removing Your API Key

### Web Dashboard
1. Go to http://localhost:8000/api_key_settings
2. Click "Clear API Key" button
3. Confirm the removal

### .env File
1. Delete the `.env` file or comment out the line
2. Restart the application

### Environment Variable
1. Unset the variable: `unset OPENAI_API_KEY`
2. Remove from shell profile if added permanently
