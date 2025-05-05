import datetime
import json
import pathlib
import shutil
import tarfile
import zipfile

from tqdm.auto import tqdm


class SkypeParser:
    def __init__(self, path: pathlib.Path, extra_logins: dict = {}):
        self.skype_path = path
        self.extra_logins = extra_logins
        self.id2name = None
        self.file_index = None
    
    def read_messages_data(self) -> dict:
        with tarfile.open(self.skype_path) as tar:
            with tar.extractfile('messages.json') as f:
                data = json.load(f)
            self.file_index = {}
            seen_files = {}
            for m in tqdm(tar.getmembers()):
                if not m.name.startswith('media/' or m.name.endswith('.json')):
                    continue
                path = pathlib.Path(m.name)
                seen_files[path.stem[:-2]] = path.name
            for m in tqdm(tar.getmembers()):
                if not (m.name.startswith('media/') and m.name.endswith('.json')):
                    continue
                meta_path = pathlib.Path(m.name)
                with tar.extractfile(m) as f:
                    media_data = json.load(f)
                    self.file_index[meta_path.stem] = seen_files[meta_path.stem]
        self.id2name = {}
        for chat in data['conversations']:
            for msg in reversed(chat['MessageList']):
                userid = self.split_username(msg['from'])
                display_name = msg['displayName']
                if display_name:
                    self.id2name.setdefault(userid, display_name)
        self.id2name.update(self.extra_logins)
        return data
    
    def split_username(self, s: str) -> str:
        return s.split(':', 1)[1]

    def find_username(self, s: str) -> str:
        assert self.id2name is not None
        userid = self.split_username(s)
        return self.id2name.get(userid, userid)
    
    def get_chats(self) -> list[dict]:
        data = self.read_messages_data()
        chats = []
        for idx, c in enumerate(data['conversations']):
            messages = c['MessageList']
            if not messages:
                continue
            chats.append({
                'index': idx,
                'id': c['id'],
                'display_name': c['displayName'],
                'num_messages': len(messages),
                'last_message_time': c['properties']['lastimreceivedtime'],
            })
        return chats
    
    def get_message_content(self, msg: dict) -> tuple[str, str]:
        import xml.etree.ElementTree as ET

        username = self.find_username(msg['from'])
        result_username = ''
        msgtype = msg['messagetype']
        content = msg['content']
        content_xml = ET.fromstring(f'<root>{content}</root>')
        files = []
        is_edit = content_xml.find('.//e_m') is not None
        match msgtype:
            case 'RichText' | 'InviteFreeRelationshipChanged/Initialized':
                result_username = username
                content = str(ET.tostring(content_xml, 'utf8', 'text'), 'utf8')
            case 'ThreadActivity/HistoryDisclosedUpdate':
                initiator = content_xml.find('.//initiator')
                content = f'{self.find_username(initiator.text)} created the chat'
            case 'ThreadActivity/AddMember':
                initiator = content_xml.find('.//initiator')
                targets = content_xml.findall('.//target')
                content = f'{self.find_username(initiator.text)} added {", ".join([self.find_username(i.text) for i in targets])}'
            case 'ThreadActivity/TopicUpdate':
                initiator = content_xml.find('.//initiator')
                value = content_xml.find('.//value')
                content = f'{self.find_username(initiator.text)} set chat name to "{value.text}"'
            case 'Event/Call':
                parlist = content_xml.find('.//partlist')
                content = f'Call {parlist.attrib["type"]}'
            case 'RichText/UriObject' | 'RichText/Media_GenericFile' | 'RichText/Media_Video' | 'RichText/Media_AudioMsg':
                result_username = username
                uriobj = content_xml.find('.//URIObject')
                if uriobj is not None:
                    docid = uriobj.attrib.get('doc_id')
                    if docid is None:
                        docid = uriobj.attrib['uri'].rsplit('/', 1)[-1]
                    filename = self.file_index.get(docid)
                    if filename is not None:
                        content = f'{filename} (file attached)'
                        files.append(filename)
                    else:
                        content = f'{content_xml.find(".//OriginalName").attrib["v"]} (file attached)'
            case 'RichText/Media_Album':
                pass  # Skip the message - content in the other messages
            case _:
                print(f'Unknown type {msgtype}')
            # valid_msg_types = {
            # 'Poll' : '***Created a poll***',
            # 'RichText/Media_CallRecording': '***Sent a call recording***',
            # 'RichText/Media_Card': '***Sent a media card***',
            # 'RichText/Media_FlikMsg': '***Sent a moji***',
            # 'RichText/ScheduledCallInvite':'***Scheduled a call***',
            # 'RichText/Location':'***Sent a location***',
            # 'RichText/Contacts':'***Sent a contact***',
            # }
        return result_username, content, files, is_edit

    def convert_chat(self, chat_idx: int, tg_data_path: pathlib.Path):
        data = self.read_messages_data()
        # userid = self.split_username(data['userId'])
        chats = data['conversations']
        chat = chats[chat_idx]
        tg_data_path.parent.mkdir(exist_ok=True, parents=True)
        all_files = []
        last_content = None
        # print(chat['threadProperties'])
        chat_name = chat['displayName']
        with zipfile.ZipFile(tg_data_path, 'w') as z:
            with z.open(f'WhatsApp Chat with {chat_name}.txt', 'w') as f:
                for message in tqdm(reversed(chat['MessageList'])):
                    try:
                        send_date = datetime.datetime.strptime(message['originalarrivaltime'], '%Y-%m-%dT%H:%M:%S.%fZ')
                    except ValueError:
                        send_date = datetime.datetime.strptime(message['originalarrivaltime'], '%Y-%m-%dT%H:%M:%SZ')
                    username, content, files, is_edit = self.get_message_content(message)
                    if is_edit and content == last_content:
                        continue
                    last_content = content
                    all_files.extend(files)
                    line = (
                        f'{send_date.month}/{send_date.day}/{send_date.year} {send_date.hour:02}:{send_date.minute:02}'
                        ' - '
                        f'{username + ": " if username else ""}{content}\n'
                    )
                    f.write(bytes(line, 'utf8'))
            with tarfile.open(self.skype_path) as tar:
                for file in set(all_files):
                    with tar.extractfile('media/' + file) as src, z.open(file, 'w') as dst:
                            shutil.copyfileobj(src, dst)

def get_chats(skype_data_path: pathlib.Path) -> list[dict]:
    parser = SkypeParser(skype_data_path)
    return parser.get_chats()


def convert_chat(skype_data_path: pathlib.Path, chat_idx: int, tg_data_path: pathlib.Path, extra_logins: dict):
    parser = SkypeParser(skype_data_path, extra_logins)
    parser.convert_chat(chat_idx, tg_data_path)
