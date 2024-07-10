import logging
import random
import string
import sqlite3
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from dotenv import load_dotenv

# Caricamento del file .env
load_dotenv()

# Configurazione del logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Stati della conversazione
(NAME, INSTAGRAM, PHONE, ADD_BOOK, BOOK_NAME, BOOK_YEAR, BOOK_SUBJECT, BOOK_CONDITION, BOOK_ISBN, BOOK_PHOTO, BOOK_PRICE, CONFIRM, DELETE_BOOK, CONFIRM_DELETE, SEARCH_BOOK) = range(15)

# ID del canale
CHANNEL_ID = "@bnlibriinvendita"

# Funzioni di gestione del database
def get_db_connection():
    conn = sqlite3.connect('bot_database.db')
    return conn, conn.cursor()

def create_tables():
    conn, c = get_db_connection()
    try:
        with conn:
            c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT, instagram TEXT, phone TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS books (code TEXT PRIMARY KEY, user_id INTEGER, message_id INTEGER, name TEXT, year TEXT, subject TEXT, condition TEXT, isbn TEXT, price TEXT, photo TEXT, FOREIGN KEY(user_id) REFERENCES users(user_id))''')
    except sqlite3.Error as e:
        logging.error(f"Errore durante la creazione delle tabelle: {e}")
    finally:
        conn.close()

def backup_database():
    import shutil
    try:
        shutil.copy('bot_database.db', 'bot_database_backup.db')
        logging.info("Backup del database creato con successo.")
    except Exception as e:
        logging.error(f"Errore durante la creazione del backup del database: {e}")

def insert_user(user_id, name, instagram, phone):
    conn, c = get_db_connection()
    try:
        with conn:
            c.execute('INSERT OR REPLACE INTO users (user_id, name, instagram, phone) VALUES (?, ?, ?, ?)', (user_id, name, instagram, phone))
    except sqlite3.Error as e:
        logging.error(f"Errore durante l'inserimento dell'utente: {e}")
    finally:
        conn.close()

def get_user(user_id):
    conn, c = get_db_connection()
    try:
        c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return c.fetchone()
    except sqlite3.Error as e:
        logging.error(f"Errore durante il recupero dell'utente: {e}")
        return None
    finally:
        conn.close()

def insert_book(code, user_id, message_id, name, year, subject, condition, isbn, price, photo):
    conn, c = get_db_connection()
    try:
        with conn:
            c.execute('INSERT INTO books (code, user_id, message_id, name, year, subject, condition, isbn, price, photo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (code, user_id, message_id, name, year, subject, condition, isbn, price, photo))
    except sqlite3.Error as e:
        logging.error(f"Errore durante l'inserimento del libro: {e}")
    finally:
        conn.close()

def delete_book_from_db(code):
    conn, c = get_db_connection()
    try:
        with conn:
            c.execute('DELETE FROM books WHERE code = ?', (code,))
    except sqlite3.Error as e:
        logging.error(f"Errore durante l'eliminazione del libro: {e}")
    finally:
        conn.close()

def get_book_by_code(code):
    conn, c = get_db_connection()
    try:
        c.execute('SELECT * FROM books WHERE code = ?', (code,))
        return c.fetchone()
    except sqlite3.Error as e:
        logging.error(f"Errore durante il recupero del libro: {e}")
        return None
    finally:
        conn.close()

def get_books_by_user(user_id):
    conn, c = get_db_connection()
    try:
        c.execute('SELECT * FROM books WHERE user_id = ?', (user_id,))
        return c.fetchall()
    except sqlite3.Error as e:
        logging.error(f"Errore durante il recupero dei libri dell'utente: {e}")
        return []
    finally:
        conn.close()

def search_book_by_isbn(isbn):
    conn, c = get_db_connection()
    try:
        c.execute('SELECT * FROM books WHERE isbn = ?', (isbn,))
        return c.fetchall()
    except sqlite3.Error as e:
        logging.error(f"Errore durante la ricerca del libro: {e}")
        return []
    finally:
        conn.close()

# Genera un codice casuale univoco
def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# Funzione per mostrare la home page
async def show_homepage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_info = get_user(context.user_data['user_id'])
    name = user_info[1] if user_info else 'utente'
    keyboard = [
        [InlineKeyboardButton("✏️ Modifica dati contatto", callback_data='modify_contact')],
        [InlineKeyboardButton("📚 Aggiungi un nuovo libro", callback_data='add_book')],
        [InlineKeyboardButton("📄 I miei annunci pubblicati", callback_data='view_announcements')],
        [InlineKeyboardButton("🔍 Cerca un libro", callback_data='search_book')],
        [InlineKeyboardButton("🔗 Canale con i libri in vendita", url=f"https://t.me/{CHANNEL_ID[1:]}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(f"🏠 Ciao *{name}*! Cosa vuoi fare?", reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(f"🏠 Ciao *{name}*! Cosa vuoi fare?", reply_markup=reply_markup, parse_mode='Markdown')
    return ADD_BOOK

# Funzione per iniziare la conversazione
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_info = get_user(update.message.from_user.id)
    if user_info:
        context.user_data['user_id'] = user_info[0]
        context.user_data['name'] = user_info[1]
        context.user_data['instagram'] = user_info[2]
        context.user_data['phone'] = user_info[3]
        context.user_data['is_logged_in'] = True
        if 'books' not in context.user_data:
            context.user_data['books'] = []
        return await show_homepage(update, context)
    else:
        context.user_data['user_id'] = update.message.from_user.id
        context.user_data['name'] = "utente non registrato"
        context.user_data['instagram'] = "no"
        context.user_data['phone'] = "3333"
        context.user_data['is_logged_in'] = False
        context.user_data['books'] = []
        await update.message.reply_text("👤 *Ciao! Per iniziare, inserisci il tuo nome e cognome:*", parse_mode='Markdown')
        return NAME

# Funzione per terminare la conversazione e tornare alla home
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Grazie! La tua conversazione è terminata.")
    elif update.message:
        await update.message.reply_text("Grazie! La tua conversazione è terminata.", reply_markup=ReplyKeyboardRemove())
    return await show_homepage(update, context)

# Funzione per ricevere il nome e cognome dell'utente
async def name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Inserisci il tuo profilo Instagram:")
    return INSTAGRAM

# Funzione per ricevere il profilo Instagram
async def instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    instagram_handle = update.message.text
    if instagram_handle.startswith('@'):
        instagram_handle = instagram_handle[1:]
    context.user_data['instagram'] = instagram_handle
    await update.message.reply_text("Inserisci il tuo numero di telefono (senza +39 e spazi):")
    return PHONE

# Funzione per ricevere il numero di telefono
async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone_number = update.message.text.replace(' ', '').replace('+39', '')
    if not phone_number.isdigit():
        await update.message.reply_text("Il numero di telefono deve contenere solo cifre. Riprova:")
        return PHONE
    context.user_data['phone'] = phone_number
    insert_user(context.user_data['user_id'], context.user_data['name'], context.user_data['instagram'], context.user_data['phone'])
    await update.message.reply_text("🔔 *Informazioni di contatto aggiornate con successo!*", parse_mode='Markdown')
    context.user_data['is_logged_in'] = True
    return await show_homepage(update, context)

# Funzione per gestire i pulsanti della keyboard inline
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if 'is_logged_in' not in context.user_data or not context.user_data['is_logged_in']:
        await query.edit_message_text("Per favore, completa le tue informazioni di contatto prima di procedere.")
        await query.message.reply_text("👤 *Ciao! Per iniziare, inserisci il tuo nome e cognome:*", parse_mode='Markdown')
        return NAME
    if query.data == 'add_book':
        await query.edit_message_text("Inserisci il nome del libro:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Torna alla home", callback_data='cancel')]]))
        return BOOK_NAME
    elif query.data == 'modify_contact':
        user_info = get_user(context.user_data['user_id'])
        current_info = (f"👤 *Dati di contatto attuali:*\n\n"
                        f"📛 *Nome:* {user_info[1]}\n"
                        f"📸 *Instagram:* {user_info[2]}\n"
                        f"📞 *Telefono:* {user_info[3]}")
        await query.edit_message_text(current_info + "\n\nInserisci il nuovo nome e cognome:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Torna alla home", callback_data='cancel')]]))
        return NAME
    elif query.data == 'view_announcements':
        return await view_announcements(update, context)
    elif query.data == 'search_book':
        await query.edit_message_text("Inserisci il codice ISBN del libro da cercare (senza spazi e trattini):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Torna alla home", callback_data='cancel')]]))
        return SEARCH_BOOK
    elif query.data == 'cancel':
        return await done(update, context)

# Funzione per ricevere il nome del libro
async def book_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['current_book'] = {
        'name': update.message.text,
        'user_id': context.user_data['user_id'],
        'name_seller': context.user_data['name'],
        'instagram': context.user_data['instagram'],
        'phone': context.user_data['phone']
    }
    keyboard = [
        ["Primo", "Secondo", "Terzo"],
        ["Quarto", "Quinto"],
        ["Primo biennio", "Secondo biennio"],
        ["Triennio", "Quinquennale"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Seleziona l'annualità del libro:", reply_markup=reply_markup)
    return BOOK_YEAR

# Funzione per ricevere l'annualità del libro
async def book_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    valid_years = ["Primo", "Secondo", "Terzo", "Quarto", "Quinto", "Primo biennio", "Secondo biennio", "Triennio", "Quinquennale"]
    if update.message.text not in valid_years:
        await update.message.reply_text("Per favore, seleziona un'annualità valida dal menu:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Torna alla home", callback_data='cancel')]]))
        return BOOK_YEAR
    context.user_data['current_book']['year'] = update.message.text
    keyboard = [
        ["#Italiano", "#Fisica", "#Storia"],
        ["#Geografia", "#Matematica", "#Scienze"],
        ["#Latino", "#Tecnologia", "#Musica"],
        ["#Arte e immagine", "#Inglese", "#Educazione civica"],
        ["#Educazione fisica", "#Religione", "#Altro"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Seleziona la materia:", reply_markup=reply_markup)
    return BOOK_SUBJECT

# Funzione per ricevere la materia del libro
async def book_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subject = update.message.text
    valid_subjects = ["#Italiano", "#Fisica", "#Storia", "#Geografia", "#Matematica", "#Scienze", "#Latino", "#Tecnologia", "#Musica", "#Arte e immagine", "#Inglese", "#Educazione civica", "#Educazione fisica", "#Religione", "#Altro"]
    if subject not in valid_subjects:
        if subject == "#Altro":
            await update.message.reply_text("Inserisci manualmente la materia:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Torna alla home", callback_data='cancel')]]))
            return BOOK_SUBJECT
        await update.message.reply_text("Per favore, seleziona una materia valida dal menu:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Torna alla home", callback_data='cancel')]]))
        return BOOK_SUBJECT
    context.user_data['current_book']['subject'] = subject
    keyboard = [
        ["Nuovo", "Come Nuovo"],
        ["Usato - Buono", "Usato - in condizioni accettabili"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Seleziona la condizione del libro:", reply_markup=reply_markup)
    return BOOK_CONDITION

# Funzione per ricevere la condizione del libro
async def book_condition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text not in ["Nuovo", "Come Nuovo", "Usato - Buono", "Usato - in condizioni accettabili"]:
        await update.message.reply_text("Per favore, seleziona una condizione valida dal menu:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Torna alla home", callback_data='cancel')]]))
        return BOOK_CONDITION
    context.user_data['current_book']['condition'] = update.message.text
    await update.message.reply_text("Inserisci l'ISBN (senza spazi e trattini):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Torna alla home", callback_data='cancel')]]))
    return BOOK_ISBN

# Funzione per ricevere l'ISBN del libro
async def book_isbn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    isbn = update.message.text.replace(' ', '').replace('-', '')
    context.user_data['current_book']['isbn'] = isbn
    keyboard = [["Sì", "No"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Vuoi aggiungere una foto del libro?", reply_markup=reply_markup)
    return BOOK_PHOTO

# Funzione per gestire la scelta dell'utente se aggiungere una foto
async def book_photo_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if choice.lower() == 'sì':
        await update.message.reply_text("Per favore, invia la foto del libro:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Torna alla home", callback_data='cancel')]]))
        return BOOK_PHOTO
    else:
        context.user_data['current_book']['photo'] = None
        keyboard = [["Salta"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Inserisci il prezzo del libro (facoltativo) o seleziona 'Salta' per saltare:", reply_markup=reply_markup)
        return BOOK_PRICE

# Funzione per ricevere la foto del libro
async def book_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['current_book']['photo'] = update.message.photo[-1].file_id
    keyboard = [["Salta"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Inserisci il prezzo del libro (facoltativo) o seleziona 'Salta' per saltare:", reply_markup=reply_markup)
    return BOOK_PRICE

# Funzione per ricevere il prezzo del libro
async def book_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price = update.message.text
    if price.lower() != 'salta':
        context.user_data['current_book']['price'] = price
    else:
        context.user_data['current_book']['price'] = None
    context.user_data['current_book']['code'] = generate_code()  # Genera un codice univoco
    await show_summary(update, context)
    return CONFIRM

# Funzione per mostrare un riepilogo delle informazioni dell'annuncio per conferma
async def show_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    book = context.user_data['current_book']
    summary = format_book_info(book)
    keyboard = [
        [InlineKeyboardButton("✅ Conferma", callback_data='confirm')],
        [InlineKeyboardButton("🏠 Torna alla home", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(f"📋 *Ecco un riepilogo del tuo annuncio:*\n\n{summary}", reply_markup=reply_markup, parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.edit_message_text(f"📋 *Ecco un riepilogo del tuo annuncio:*\n\n{summary}", reply_markup=reply_markup, parse_mode='Markdown')
    return CONFIRM

# Funzione per confermare l'aggiunta del libro e inviarlo al canale
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == 'confirm':
        await query.answer()
        book = context.user_data['current_book']
        context.user_data['books'].append(book)  # Aggiunge il libro ai libri salvati
        message = await send_book_info_to_channel(context.bot, book)  # Invia le informazioni al canale e ottiene il messaggio inviato
        insert_book(book['code'], book['user_id'], message.message_id, book['name'], book['year'], book['subject'], book['condition'], book['isbn'], book['price'], book['photo'])
        await query.edit_message_text("📚 *Libro confermato e aggiunto con successo al canale!*", parse_mode='Markdown')
        context.user_data.pop('current_book', None)  # Rimuove il libro corrente dai dati utente
    return await show_homepage(update, context)

# Funzione per annullare l'operazione e tornare alla home page
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == 'cancel':
        await query.answer()
        await show_homepage(update, context)
        return ConversationHandler.END

# Funzione per inviare le informazioni del libro al canale Telegram
async def send_book_info_to_channel(bot, book):
    message = format_book_info(book)
    if 'photo' in book and book['photo']:
        sent_message = await bot.send_photo(chat_id=CHANNEL_ID, photo=book['photo'], caption=message, parse_mode='Markdown')
    else:
        sent_message = await bot.send_message(chat_id=CHANNEL_ID, text=message, parse_mode='Markdown')
    return sent_message

# Funzione per formattare le informazioni del libro per la visualizzazione
def format_book_info(book):
    contact_info_telegram = f"tg://user?id={book['user_id']}"
    contact_info_whatsapp = f"https://wa.me/+39{book['phone']}"
    contact_info_instagram = f"https://instagram.com/{book['instagram']}"
    return (f"📖 **Nome del libro:** *{book['name']}*\n"
            f"📅 **Anno:** {book['year']}\n"
            f"📚 **Materia:** {book['subject']}\n"
            f"📋 **Condizione:** {book['condition']}\n"
            f"🔢 **ISBN:** `{book['isbn']}`\n"
            f"💵 **Prezzo:** {book['price'] if book['price'] else 'Non fornito'}\n"
            f"👤 **Venditore:** {book['name_seller']}\n"
            f"📩 [Contatta il venditore su Telegram]({contact_info_telegram})\n"
            f"📩 [Contatta su WhatsApp]({contact_info_whatsapp})\n"
            f"📩 Instagram: [{book['instagram']}]({contact_info_instagram})")

# Funzione per mostrare gli annunci pubblicati
async def view_announcements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data['user_id']
    books = get_books_by_user(user_id)

    if not books:
        await update.callback_query.edit_message_text("Non hai nessun annuncio pubblicato.")
        return await show_homepage(update, context)

    keyboard = [[InlineKeyboardButton(book[3], callback_data=f"delete_{book[0]}")] for book in books]  # book[3] è il titolo del libro, book[0] è il codice
    keyboard.append([InlineKeyboardButton("🏠 Torna alla home", callback_data='cancel')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("📄 *I tuoi annunci pubblicati:*\nSeleziona un libro per eliminarlo.", reply_markup=reply_markup, parse_mode='Markdown')
    return DELETE_BOOK

# Funzione per eliminare un libro selezionato dal canale
async def select_book_to_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    code = query.data.split("_")[1]
    book = get_book_by_code(code)

    if book and book[1] == context.user_data['user_id']:
        keyboard = [
            [InlineKeyboardButton("🗑️ Elimina questo annuncio", callback_data=f"confirm_delete_{code}")],
            [InlineKeyboardButton("🏠 Torna alla home", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Sei sicuro di voler eliminare l'annuncio per il libro *{book[3]}*?", reply_markup=reply_markup, parse_mode='Markdown')
        return CONFIRM_DELETE
    else:
        await query.edit_message_text("❌ *Codice non trovato o non hai il permesso di eliminare questo libro.*", parse_mode='Markdown')
        return await show_homepage(update, context)

# Funzione per confermare l'eliminazione di un libro
async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    code = query.data.split("_")[2]
    book = get_book_by_code(code)

    if book and book[1] == context.user_data['user_id']:
        await context.bot.delete_message(chat_id=CHANNEL_ID, message_id=book[2])
        await query.edit_message_text("🗑️ *Libro eliminato con successo dal canale!*", parse_mode='Markdown')
        delete_book_from_db(code)
    else:
        await query.edit_message_text("❌ *Codice non trovato o non hai il permesso di eliminare questo libro.*", parse_mode='Markdown')

    return await show_homepage(update, context)

# Funzione per cercare un libro in vendita
async def search_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    isbn = update.message.text.replace(' ', '').replace('-', '')
    books = search_book_by_isbn(isbn)
    if books:
        await update.message.reply_text("📚 Sì, il libro è in vendita nel canale: https://t.me/bnlibriinvendita")
    else:
        await update.message.reply_text("❌ Il libro non è in vendita nel canale.")
    return await show_homepage(update, context)

# Caricamento del token e inizializzazione del bot
if __name__ == '__main__':
    token = os.getenv('TELEGRAM_TOKEN')
    create_tables()
    backup_database()
    application = ApplicationBuilder().token(token).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
            INSTAGRAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, instagram)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone)],
            ADD_BOOK: [CallbackQueryHandler(button)],
            BOOK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_name)],
            BOOK_YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_year)],
            BOOK_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_subject)],
            BOOK_CONDITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_condition)],
            BOOK_ISBN: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_isbn)],
            BOOK_PHOTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_photo_choice), MessageHandler(filters.PHOTO, book_photo)],
            BOOK_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_price)],
            CONFIRM: [CallbackQueryHandler(confirm, pattern='confirm'), CallbackQueryHandler(cancel, pattern='cancel')],
            DELETE_BOOK: [CallbackQueryHandler(confirm_delete, pattern=r'^confirm_delete_')],
            SEARCH_BOOK: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_book)]
        },
        fallbacks=[CommandHandler('done', done), CommandHandler('start', show_homepage), CallbackQueryHandler(done, pattern='cancel')]
    )
    application.add_handler(conv_handler)
    application.run_polling()
