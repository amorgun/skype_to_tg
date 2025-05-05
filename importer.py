import contextlib
import functools
import itertools
import pathlib
import mimetypes
import zipfile

from PIL import Image
from telethon import functions, types
from telethon.sync import TelegramClient
from tqdm.auto import tqdm


class Importer:
    def __init__(self, app_name: str, api_id: str, api_hash: str):
        self.app_name = app_name
        self.api_id = api_id
        self.api_hash = api_hash

    def import_chat(self, export_path: pathlib.Path, peer_id: str):
        # from https://github.com/filippz/telegram_import/tree/master
        with contextlib.ExitStack() as st:
            zfile = st.enter_context(zipfile.ZipFile(export_path, 'r'))
            messages_file = None
            attachment_files = []
            for file in tqdm(zfile.namelist()):
                if file.startswith('WhatsApp Chat with ') and file.endswith('.txt'):
                    messages_file = file
                else:
                    file_data = {
                        'name': file,
                        'mime_type': mimetypes.guess_type(file)[0],
                    }
                    if file_data['mime_type'] == "image/jpeg":
                        file_data['type'] = types.InputMediaUploadedPhoto
                    else:
                        file_data['type'] = types.InputMediaUploadedDocument
                        if file_data['mime_type'].startswith('image/'):
                            with zfile.open(file, 'r') as f:
                                img = Image.open(f)
                            height, width = img.size 
                            file_data['type'] = functools.partial(file_data['type'], attributes=[types.DocumentAttributeImageSize(width, height)], mime_type=file_data['mime_type'])
                    attachment_files.append(file_data)
            # import collections
            # print(collections.Counter(i['mime_type'] for i in attachment_files).most_common())
            # for i in attachment_files:
            #     if i['mime_type'] not in ('image/jpeg', 'image/png'):
            #         print(i) 

            messages_file_obj = st.enter_context(zfile.open(messages_file, 'r'))
            messages_head = ''.join(str(i, 'utf8') for i in itertools.islice(messages_file_obj, 100))
            messages_file_obj.seek(0)
            # print(messages_head)

            # return
            client = st.enter_context(TelegramClient(self.app_name, self.api_id, self.api_hash))
            # peer = client.get_entity(types.PeerChannel(int(peer_id)))
            peer = peer_id
            print(peer)

            # check if Telegram API understands the import file based on first 100 rows
            client(functions.messages.CheckHistoryImportRequest(
                import_head=messages_head
            ))

            # check if the peer is OK for import
            client(functions.messages.CheckHistoryImportPeerRequest(
                peer=peer
            ))

            # create temporary file to store actual messages

            # initiate actual import
            print("Starting import")
            history_import = client(functions.messages.InitHistoryImportRequest(
                peer=peer,
                file=client.upload_file(messages_file_obj),
                media_count=len(attachment_files)
            ))

            # upload being mentioned in messages
            print("Upload files mentioned in messages")

            pbar = tqdm(attachment_files)
            for file_data in pbar:
                file = st.enter_context(zfile.open(file_data['name'], 'r'))
                input_file = client.upload_file(file)
                pbar.set_description("Uploading {filename}".format(filename=file_data['name']))
                client(functions.messages.UploadImportedMediaRequest(
                    peer=peer,
                    import_id=history_import.id,
                    file_name=file_data['name'],
                    media=file_data['type'](file=input_file)
                ))

            # messages are there and all the files they are mentioning, so we can now complete the actual import process
            client(functions.messages.StartHistoryImportRequest(
                peer=peer,
                import_id=history_import.id
            ))
            print("Import complete")
