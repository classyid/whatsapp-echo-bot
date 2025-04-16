import asyncio
import logging
import signal
import sys
from neonize.aioze.client import NewAClient
from neonize.events import (
    ConnectedEv,
    MessageEv,
    PairStatusEv,
    event,
)
from neonize.utils import log
from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message

# Mengatur level logging
log.setLevel(logging.INFO)

# Event untuk sinyal penghentian program
stop_event = asyncio.Event()

# Membuat client instance
client = NewAClient("wa_session.sqlite3")

@client.event(ConnectedEv)
async def on_connected(_: NewAClient, __: ConnectedEv):
    """Handler untuk event saat client terhubung"""
    log.info("⚡ Client terhubung ke WhatsApp")
    log.info("Bot siap menerima pesan. Kirim pesan apapun untuk mendapatkan echo.")

@client.event(PairStatusEv)
async def on_pair_status(_: NewAClient, message: PairStatusEv):
    """Handler untuk event saat status pair berubah (login berhasil)"""
    try:
        user_id = message.ID.User if hasattr(message.ID, 'User') else "unknown"
        log.info(f"Berhasil login sebagai {user_id}")
    except Exception as e:
        log.error(f"Error saat mendapatkan user ID: {e}")

@client.event(MessageEv)
async def on_message(client: NewAClient, message: MessageEv):
    """Handler untuk event saat menerima pesan - Echo semua jenis media"""
    try:
        # Mendapatkan info chat
        chat = None
        if hasattr(message.Info.MessageSource, 'Chat'):
            chat = message.Info.MessageSource.Chat
        else:
            log.error("Tidak bisa mendapatkan chat ID dari pesan")
            return
        
        # Mendapatkan info sender
        sender = ""
        if hasattr(message.Info.MessageSource, 'Sender'):
            sender = message.Info.MessageSource.Sender
        
        # Perintah khusus untuk ping dan stop
        is_command = False
        if hasattr(message.Message, 'conversation'):
            text = message.Message.conversation
            if text.lower() == "ping":
                await client.send_message(chat, Message(conversation="pong"))
                log.info("Berhasil membalas 'pong'")
                is_command = True
            elif text.lower() in ["stop", "exit", "quit"]:
                await client.send_message(chat, Message(conversation="Mematikan bot..."))
                log.info("Menerima perintah stop dari pengguna")
                await stop_bot()
                is_command = True
        elif hasattr(message.Message, 'extendedTextMessage'):
            text = message.Message.extendedTextMessage.text
            if text.lower() == "ping":
                await client.send_message(chat, Message(conversation="pong"))
                is_command = True
            elif text.lower() in ["stop", "exit", "quit"]:
                await client.send_message(chat, Message(conversation="Mematikan bot..."))
                await stop_bot()
                is_command = True
        
        # Jika bukan perintah khusus, echo pesan
        if not is_command:
            log.info(f"Menerima pesan dari {sender}, akan melakukan echo")
            
            # Coba echo pesan dengan cara yang lebih langsung
            try:
                # Kirim kembali pesan asli persis seperti yang diterima
                await client.send_message(chat, message.Message)
                log.info("Berhasil melakukan echo pesan")
            except Exception as echo_error:
                log.error(f"Error saat echo pesan: {echo_error}")
                
                # Coba cara alternatif jika cara langsung gagal
                try:
                    if hasattr(message.Message, 'conversation'):
                        # Pesan teks biasa
                        await client.send_message(chat, Message(conversation=message.Message.conversation))
                        log.info("Berhasil echo teks biasa")
                    elif hasattr(message.Message, 'extendedTextMessage'):
                        # Extended text
                        await client.send_message(chat, Message(conversation=message.Message.extendedTextMessage.text))
                        log.info("Berhasil echo extended text sebagai teks biasa")
                    elif hasattr(message.Message, 'imageMessage'):
                        # Pesan gambar
                        if hasattr(message.Message.imageMessage, 'url') and message.Message.imageMessage.url:
                            # Gunakan URL gambar untuk mengirim ulang
                            url = message.Message.imageMessage.url
                            caption = message.Message.imageMessage.caption if hasattr(message.Message.imageMessage, 'caption') else ""
                            
                            log.info(f"Mencoba kirim ulang gambar dari URL: {url}")
                            await client.send_image(chat, url, caption=caption)
                            log.info("Berhasil echo gambar")
                    elif hasattr(message.Message, 'videoMessage'):
                        # Pesan video
                        if hasattr(message.Message.videoMessage, 'url') and message.Message.videoMessage.url:
                            # Gunakan URL video untuk mengirim ulang
                            url = message.Message.videoMessage.url
                            caption = message.Message.videoMessage.caption if hasattr(message.Message.videoMessage, 'caption') else ""
                            
                            log.info(f"Mencoba kirim ulang video dari URL: {url}")
                            await client.send_video(chat, url, caption=caption)
                            log.info("Berhasil echo video")
                    elif hasattr(message.Message, 'audioMessage'):
                        # Pesan audio / voice note
                        if hasattr(message.Message.audioMessage, 'url') and message.Message.audioMessage.url:
                            # Gunakan URL audio untuk mengirim ulang
                            url = message.Message.audioMessage.url
                            is_voice = message.Message.audioMessage.ptt if hasattr(message.Message.audioMessage, 'ptt') else False
                            
                            log.info(f"Mencoba kirim ulang {'voice note' if is_voice else 'audio'} dari URL: {url}")
                            await client.send_audio(chat, url, ptt=is_voice)
                            log.info(f"Berhasil echo {'voice note' if is_voice else 'audio'}")
                    elif hasattr(message.Message, 'documentMessage'):
                        # Pesan dokumen
                        if hasattr(message.Message.documentMessage, 'url') and message.Message.documentMessage.url:
                            # Gunakan URL dokumen untuk mengirim ulang
                            url = message.Message.documentMessage.url
                            filename = message.Message.documentMessage.fileName if hasattr(message.Message.documentMessage, 'fileName') else "document"
                            
                            log.info(f"Mencoba kirim ulang dokumen dari URL: {url}")
                            await client.send_document(chat, url, filename=filename)
                            log.info("Berhasil echo dokumen")
                    elif hasattr(message.Message, 'locationMessage'):
                        # Pesan lokasi
                        latitude = message.Message.locationMessage.degreesLatitude
                        longitude = message.Message.locationMessage.degreesLongitude
                        
                        log.info(f"Mencoba echo lokasi: {latitude}, {longitude}")
                        await client.send_message(chat, Message(locationMessage=message.Message.locationMessage))
                        log.info("Berhasil echo lokasi")
                    elif hasattr(message.Message, 'stickerMessage'):
                        # Pesan stiker
                        if hasattr(message.Message.stickerMessage, 'url') and message.Message.stickerMessage.url:
                            url = message.Message.stickerMessage.url
                            
                            log.info(f"Mencoba kirim ulang stiker dari URL: {url}")
                            await client.send_sticker(chat, url)
                            log.info("Berhasil echo stiker")
                    else:
                        # Tipe pesan tidak dikenali atau tidak didukung
                        await client.send_message(chat, Message(conversation="Tipe pesan tidak didukung untuk echo."))
                        log.info("Tipe pesan tidak didukung untuk echo")
                except Exception as alt_error:
                    log.error(f"Error saat echo dengan cara alternatif: {alt_error}")
                    await client.send_message(chat, Message(conversation="Tidak bisa melakukan echo untuk pesan ini."))
    
    except Exception as e:
        log.error(f"Error saat memproses pesan: {e}")
        import traceback
        log.error(traceback.format_exc())

async def stop_bot():
    """Fungsi untuk menghentikan bot dengan bersih"""
    log.info("Proses penghentian bot dimulai...")
    try:
        # Logout dari WhatsApp
        log.info("Melakukan logout dari WhatsApp...")
        await client.logout()
        log.info("Logout berhasil")
    except Exception as e:
        log.error(f"Error saat logout: {e}")
    
    # Set event untuk mengakhiri loop utama
    stop_event.set()

# Daftarkan handler SIGINT
signal.signal(signal.SIGINT, lambda s, f: asyncio.get_event_loop().create_task(stop_bot()))

async def main():
    """Fungsi utama"""
    log.info("Memulai client WhatsApp...")
    log.info("QR code akan muncul jika perlu login. Silakan scan...")
    log.info("Tekan Ctrl+C untuk berhenti atau kirim pesan 'stop' ke bot")
    
    try:
        # Connect dan tunggu hingga interrupsi
        connection_task = asyncio.create_task(client.connect())
        
        # Menunggu event penghentian
        await stop_event.wait()
        log.info("Event penghentian diterima, menutup program...")
        
    except Exception as e:
        log.error(f"Error saat menjalankan client: {e}")
    finally:
        log.info("Client berhenti")

if __name__ == "__main__":
    # Jalankan di loop asyncio
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        log.info("Program dihentikan oleh pengguna")
    finally:
        log.info("Program selesai")
