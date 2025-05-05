# skype_to_tg
Tools for migrating your chat history from Skype to Telegram, including text history as well as sent photos and files.  
This is done by converting Skype chat exports to WhatsApp export format and importing it to Telegram. 

## Getting started
1. Clone/download this repository,
    ```sh
    git clone https://github.com/amorgun/skype_to_tg.git
    ```
2. Install requirements
    ```sh
    pip install -r skype_to_tg/requirements.txt
    ```
3. Register a Telergamm App [here](https://my.telegram.org/apps) and write your `app_name`, `api_id` and `app_hash` to `config.json` 

## Usage
1. Export your chats from Skype [here](https://secure.skype.com/en/data-export)
2. See the list of exported chats using
    ```sh
    python skype_to_tg chats '<path to your export .tar>'
    ```
    **Example**:
    ```sh
    python skype_to_tg chats 'C:\Users\alice\skype_to_tg\8_alice_export.tar'
   ```
3. Select a single chat from the list and export it using
    ```sh
    python skype_to_tg convert '<path to your export .tar>' <chat_id> '<path to save chat .zip>
    ```
    **Example**:
    ```sh
    python skype_to_tg convert 'C:\Users\alice\skype_to_tg\8_alice_export.tar' '0' 'C:\Users\alice\skype_to_tg\chat_with_joe.zip'
    ```
4. Import the converted chat to Telegram
    ```sh
    python skype_to_tg import '<path to chat .zip>' 'config.json'  <peer>
    ```
    You can use user login as a `peer`

    **Example**:
    ```sh
    python skype_to_tg import 'C:\Users\alice\skype_to_tg\chat_with_joe.zip' 'config.json' 'joe'
    ```

## Telegram requirements
To import chat history Telegram requires you to be mutual contacts with the peer and have a private chat started.  
It also cannot import group chats.