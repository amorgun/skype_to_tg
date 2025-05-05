import argparse
import json
import pathlib

from parser import get_chats, convert_chat
from importer import Importer


def do_parse_chats(args):
    chats = get_chats(args.input)
    if not chats:
        print('No chats found')
        return
    print(f'Chat ID\tLast message ts\t# of messages\tChat name')
    for c in chats:
        last_message_time = c.get('last_message_time')
        if last_message_time:
            last_message_time = last_message_time[:16]
        else:
            last_message_time ='         unknown'
        display_name = c.get('display_name')
        if not display_name:
            continue
        display_name = display_name.strip()
        print(f'{c["index"]}\t{last_message_time}\t{c["num_messages"]}\t{display_name}')


def do_convert_chat(args):
    extra_logins = {}
    for val in args.extra_login or []:
        parts = val.split(':', 1)
        if len(parts) != 2:
            raise ValueError(f'Expected "login:displayname" pair, got {val}')
        extra_logins[parts[0]] = parts[1]
    convert_chat(args.input, args.chat_id, args.output, extra_logins)


def import_chat(args):
    with args.config.open('r') as f:
        config = json.load(f)
    importer = Importer(config['app_name'], config['api_id'], config['api_hash'])
    importer.import_chat(args.input, args.peer)


if __name__ == '__main__':
    root_parser = argparse.ArgumentParser(description='Convert Skype export to the Telegram importable format')
    subparsers = root_parser.add_subparsers()
    chats_parser = subparsers.add_parser('chats', help='Get list of chats')
    chats_parser.add_argument('input', help='Path to the skype export .tar file', type=pathlib.Path)
    chats_parser.set_defaults(func=do_parse_chats)
    convert_parser = subparsers.add_parser('convert', help='Get a single chat and convert it to the Telegram format')
    convert_parser.add_argument('input', help='Path to the skype export .tar file', type=pathlib.Path)
    convert_parser.add_argument('chat_id', help='Id of the exported chat', type=int)
    convert_parser.add_argument('output', help='Path to the result', type=pathlib.Path)
    convert_parser.add_argument('-e', '--extra_login',  nargs='*', help='Login to name overrides in the form "login:displaynames"')
    convert_parser.set_defaults(func=do_convert_chat)
    import_parser = subparsers.add_parser('import', help='Import an exported chat into Telegram')
    import_parser.add_argument('input', help='Path to the export .zip file', type=pathlib.Path)
    import_parser.add_argument('config', help='Path to json with your api hash and api id', type=pathlib.Path)
    import_parser.add_argument('peer', help='Phone of the target user', type=str)
    import_parser.set_defaults(func=import_chat)
    args = root_parser.parse_args()
    args.func(args)
