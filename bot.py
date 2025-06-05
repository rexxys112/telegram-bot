
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# ========== DATABASE SEMENTARA ==========
user_tasks = {}  # Simpan garapan + status per user
user_input_state = {}  # Simpan state "sedang input" garapan
user_categories = {}  # Simpan kategori custom per user

# Default categories
DEFAULT_CATEGORIES = ["dayli", "testnet", "mining"]

def get_user_categories(user_id):
    """Get categories for user (default + custom)"""
    if user_id not in user_categories:
        user_categories[user_id] = DEFAULT_CATEGORIES.copy()
    return user_categories[user_id]

def get_main_menu(user_id):
    """Generate main menu based on user's categories"""
    categories = get_user_categories(user_id)
    menu = []
    
    # Buat baris untuk kategori (2 per baris)
    for i in range(0, len(categories), 2):
        row = []
        row.append(InlineKeyboardButton(f"garapan {categories[i]}", callback_data=categories[i]))
        if i + 1 < len(categories):
            row.append(InlineKeyboardButton(f"garapan {categories[i+1]}", callback_data=categories[i+1]))
        menu.append(row)
    
    # Tambah tombol add/remove
    menu.append([
        InlineKeyboardButton("➕ add garapan", callback_data="add_garapan"),
        InlineKeyboardButton("➖ remove garapan", callback_data="remove_garapan")
    ])
    
    return menu

# ========== START ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    keyboard = InlineKeyboardMarkup(get_main_menu(user_id))
    await update.message.reply_text("🚀 Selamat datang! Pilih kategori garapan:", reply_markup=keyboard)

# ========== TAMPILKAN GARAPAN (dayli/testnet/mining) ==========
async def show_project_list(query, user_id, tipe):
    data = user_tasks[user_id].get(tipe, {})
    keyboard = []
    
    # Tampilkan list garapan
    for name in data:
        done = data[name]["done"]
        icon = "✅" if done else "❌"
        keyboard.append([InlineKeyboardButton(f"{name} {icon}", callback_data=f"{tipe}|{name}")])
    
    # Tambah tombol "Add Garapan" dan "Remove Garapan" untuk setiap kategori
    if data:  # Hanya tampilkan remove jika ada data
        keyboard.append([
            InlineKeyboardButton(f"➕ Add Garapan {tipe.title()}", callback_data=f"add_{tipe}"),
            InlineKeyboardButton(f"🗑️ Remove Garapan", callback_data=f"remove_{tipe}")
        ])
    else:
        keyboard.append([InlineKeyboardButton(f"➕ Add Garapan {tipe.title()}", callback_data=f"add_{tipe}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Menu Utama", callback_data="main_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"📋 Garapan {tipe} kamu:", reply_markup=reply_markup)

# ========== TAMPILKAN MENU ==========
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "main_menu":
        keyboard = InlineKeyboardMarkup(get_main_menu(user_id))
        await query.edit_message_text("🚀 Selamat datang! Pilih kategori garapan:", reply_markup=keyboard)
        
    # Handle semua kategori secara dinamis
    elif query.data in get_user_categories(user_id):
        # Initialize user data jika belum ada
        if user_id not in user_tasks:
            user_tasks[user_id] = {}
        
        # Cek apakah user sudah punya data untuk kategori ini
        if not user_tasks[user_id].get(query.data):
            # Belum ada data, suruh add dulu
            keyboard = [
                [InlineKeyboardButton(f"➕ Add Data {query.data.title()}", callback_data=f"add_{query.data}")],
                [InlineKeyboardButton("🔙 Menu Utama", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"⚠️ Kamu belum punya data garapan {query.data}.\n📝 Silakan add data {query.data} dulu!", 
                reply_markup=reply_markup
            )
        else:
            # Sudah ada data, tampilkan list
            await show_project_list(query, user_id, query.data)
            
    # Handle add data untuk semua kategori secara dinamis
    elif query.data.startswith("add_") and not query.data == "add_garapan":
        kategori = query.data.replace("add_", "")
        user_input_state[user_id] = f"step1_{kategori}_nama"
        await query.edit_message_text(
            f"📝 <b>Tambah Garapan {kategori.title()}</b>\n\n"
            "🏷️ <b>Step 1/6:</b> Masukkan <b>Nama Project</b>\n\n"
            "Contoh: <i>Lenscan Protocol</i>\n\n"
            "💡 <i>Ketik nama project yang ingin ditambahkan</i>",
            parse_mode="HTML"
        )
        
    # Handle remove garapan untuk setiap kategori
    elif query.data.startswith("remove_") and not query.data == "remove_garapan":
        kategori = query.data.replace("remove_", "")
        
        if user_id in user_tasks and kategori in user_tasks[user_id] and user_tasks[user_id][kategori]:
            data = user_tasks[user_id][kategori]
            keyboard = []
            
            # Tampilkan list garapan untuk dihapus
            for name in data:
                keyboard.append([InlineKeyboardButton(f"🗑️ Hapus '{name}'", callback_data=f"delete_{kategori}|{name}")])
            
            keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data=kategori)])
            
            await query.edit_message_text(
                f"🗑️ <b>Hapus Garapan {kategori.title()}</b>\n\n"
                "Pilih garapan yang ingin dihapus:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text(
                f"❌ Tidak ada garapan {kategori} untuk dihapus!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data=kategori)]])
            )
    
    # Handle delete specific garapan
    elif query.data.startswith("delete_"):
        data_part = query.data.replace("delete_", "")
        kategori, name = data_part.split("|")
        
        if user_id in user_tasks and kategori in user_tasks[user_id] and name in user_tasks[user_id][kategori]:
            del user_tasks[user_id][kategori][name]
            
            await query.edit_message_text(
                f"✅ <b>Garapan '{name}' berhasil dihapus!</b>\n\n"
                f"🗂️ Garapan {kategori} telah diperbarui.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data=kategori)]]),
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text(
                "❌ Garapan tidak ditemukan!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data=kategori)]])
            )
        
    # Handle remove category
    elif query.data.startswith("remove_cat_"):
        category_to_remove = query.data.replace("remove_cat_", "")
        categories = get_user_categories(user_id)
        
        if category_to_remove in categories:
            categories.remove(category_to_remove)
            # Hapus data garapan kategori tersebut juga
            if user_id in user_tasks and category_to_remove in user_tasks[user_id]:
                del user_tasks[user_id][category_to_remove]
            
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Utama", callback_data="main_menu")]])
            await query.edit_message_text(
                f"✅ Kategori '{category_to_remove}' berhasil dihapus!\n"
                f"🗂️ Sisa kategori: {', '.join(categories)}",
                reply_markup=keyboard
            )
        else:
            await query.edit_message_text("❌ Kategori tidak ditemukan!")
        
    elif query.data == "add_garapan":
        user_input_state[user_id] = "awaiting_new_category"
        await query.edit_message_text(
            "➕ <b>Tambah Kategori Garapan Baru</b>\n\n"
            "Silakan kirim nama kategori baru yang ingin ditambahkan.\n"
            "Contoh: gaming, social, defi, nft, etc.\n\n"
            "💡 <i>Kategori akan otomatis ditambahkan ke menu utama</i>",
            parse_mode="HTML"
        )
        
    elif query.data == "remove_garapan":
        categories = get_user_categories(user_id)
        if len(categories) <= 1:
            await query.edit_message_text(
                "⚠️ Tidak bisa menghapus kategori karena hanya tersisa 1 atau kurang.\n"
                "Minimal harus ada 1 kategori garapan!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Utama", callback_data="main_menu")]])
            )
            return
            
        keyboard = []
        for cat in categories:
            keyboard.append([InlineKeyboardButton(f"🗑️ Hapus '{cat}'", callback_data=f"remove_cat_{cat}")])
        keyboard.append([InlineKeyboardButton("🔙 Menu Utama", callback_data="main_menu")])
        
        await query.edit_message_text(
            "➖ <b>Hapus Kategori Garapan</b>\n\n"
            "Pilih kategori yang ingin dihapus:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

# ========== HANDLE INPUT GARAPAN USER ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in user_input_state:
        if user_input_state[user_id] == "awaiting_new_category":
            # Handle input kategori baru
            new_category = update.message.text.strip().lower()
            if not new_category:
                await update.message.reply_text("❌ Nama kategori tidak boleh kosong!")
                return
                
            categories = get_user_categories(user_id)
            if new_category in categories:
                await update.message.reply_text(f"⚠️ Kategori '{new_category}' sudah ada!")
                return
                
            categories.append(new_category)
            del user_input_state[user_id]
            await update.message.reply_text(f"✅ Kategori '{new_category}' berhasil ditambahkan!\n🗂️ Total kategori: {', '.join(categories)}")
            
        # Handle step-by-step input
        elif user_input_state[user_id].startswith("step"):
            await handle_step_input(update, context, user_id)
            
    else:
        await update.message.reply_text("⚠️ Kirim /start untuk mulai.")

# ========== HANDLE STEP-BY-STEP INPUT ==========
async def handle_step_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    state = user_input_state[user_id]
    user_input = update.message.text.strip()
    
    # Initialize user data if not exists
    if user_id not in user_tasks:
        user_tasks[user_id] = {}
    if f"{user_id}_temp" not in user_tasks:
        user_tasks[f"{user_id}_temp"] = {}
    
    # Parse state: stepX_kategori_field
    parts = state.split("_")
    step = parts[0]
    kategori = parts[1]
    field = parts[2] if len(parts) > 2 else ""
    
    # Initialize temp data for this category
    if kategori not in user_tasks[f"{user_id}_temp"]:
        user_tasks[f"{user_id}_temp"][kategori] = {}
    
    if step == "step1":  # Nama
        user_tasks[f"{user_id}_temp"][kategori]["nama"] = user_input
        user_input_state[user_id] = f"step2_{kategori}_web"
        await update.message.reply_text(
            f"✅ <b>Nama:</b> {user_input}\n\n"
            f"🌐 <b>Step 2/6:</b> Masukkan <b>Link Web</b>\n\n"
            "Contoh: <i>https://lenscan.io/apps</i>\n\n"
            "💡 <i>Masukkan URL website utama project</i>",
            parse_mode="HTML"
        )
        
    elif step == "step2":  # Web
        user_tasks[f"{user_id}_temp"][kategori]["web"] = user_input
        user_input_state[user_id] = f"step3_{kategori}_faucet"
        await update.message.reply_text(
            f"✅ <b>Web:</b> {user_input}\n\n"
            f"🚰 <b>Step 3/6:</b> Masukkan <b>Link Faucet</b>\n\n"
            "Contoh: <i>https://testnet.lenscan.io/faucet</i>\n\n"
            "💡 <i>Jika tidak ada faucet, ketik 'tidak ada'</i>",
            parse_mode="HTML"
        )
        
    elif step == "step3":  # Faucet
        user_tasks[f"{user_id}_temp"][kategori]["faucet"] = user_input
        user_input_state[user_id] = f"step4_{kategori}_links"
        await update.message.reply_text(
            f"✅ <b>Faucet:</b> {user_input}\n\n"
            f"🔗 <b>Step 4/6:</b> Masukkan <b>Link Tambahan</b>\n\n"
            "Contoh:\n"
            "<i>Reputation: https://lensreputation.xyz/\n"
            "Bridge: https://portal.testnet.lens.dev/bridge/\n"
            "Lens Profile: https://onboarding.lens.xyz/</i>\n\n"
            "💡 <i>Satu link per baris. Jika tidak ada, ketik 'tidak ada'</i>",
            parse_mode="HTML"
        )
        
    elif step == "step4":  # Links tambahan
        user_tasks[f"{user_id}_temp"][kategori]["links"] = user_input
        user_input_state[user_id] = f"step5_{kategori}_cara"
        await update.message.reply_text(
            f"✅ <b>Link Tambahan:</b>\n{user_input}\n\n"
            f"📝 <b>Step 5/6:</b> Masukkan <b>Cara Garap</b>\n\n"
            "Contoh:\n"
            "<i>- Daftar semua ecosystem\n"
            "- Follow People\n"
            "- Active Post, Like, Retweet Dll\n"
            "- Mint NFT di Ecosystem nya\n"
            "- Register: Bridge\n"
            "- Connect Wallet\n"
            "- Bridge from Lens Network to Sepolia\n"
            "- Done</i>\n\n"
            "💡 <i>Tuliskan step-by-step cara kerja project ini</i>",
            parse_mode="HTML"
        )
        
    elif step == "step5":  # Cara garap
        user_tasks[f"{user_id}_temp"][kategori]["cara"] = user_input
        user_input_state[user_id] = f"step6_{kategori}_confirm"
        
        # Show preview
        temp_data = user_tasks[f"{user_id}_temp"][kategori]
        preview = f"""📋 <b>Preview Data Garapan {kategori.title()}</b>

🏷️ <b>Nama:</b> {temp_data['nama']}
🌐 <b>Web:</b> {temp_data['web']}
🚰 <b>Faucet:</b> {temp_data['faucet']}

🔗 <b>Link Tambahan:</b>
{temp_data['links']}

📝 <b>Cara Garap:</b>
{temp_data['cara']}

<b>Step 6/6:</b> Konfirmasi data diatas
Ketik <b>'ya'</b> untuk menyimpan atau <b>'tidak'</b> untuk membatalkan"""
        
        await update.message.reply_text(preview, parse_mode="HTML")
        
    elif step == "step6":  # Konfirmasi
        if user_input.lower() in ['ya', 'yes', 'y', 'iya', 'ok']:
            # Save data
            temp_data = user_tasks[f"{user_id}_temp"][kategori]
            
            # Format data untuk disimpan
            nama = temp_data['nama']
            formatted_data = {
                "web": temp_data['web'],
                "faucet": temp_data['faucet'],
                "cara": f"{temp_data['links']}\n\nCARA GARAP:\n{temp_data['cara']}",
                "done": False
            }
            
            # Simpan ke user_tasks
            if kategori not in user_tasks[user_id]:
                user_tasks[user_id][kategori] = {}
            user_tasks[user_id][kategori][nama] = formatted_data
            
            # Cleanup
            del user_tasks[f"{user_id}_temp"][kategori]
            del user_input_state[user_id]
            
            await update.message.reply_text(
                f"✅ <b>Garapan {kategori} berhasil disimpan!</b>\n\n"
                f"📌 <b>{nama}</b> telah ditambahkan ke daftar garapan {kategori} kamu.\n\n"
                f"🔄 Ketik /start untuk kembali ke menu utama.",
                parse_mode="HTML"
            )
        else:
            # Batalkan
            del user_tasks[f"{user_id}_temp"][kategori]
            del user_input_state[user_id]
            await update.message.reply_text(
                "❌ <b>Input dibatalkan!</b>\n\n"
                "🔄 Ketik /start untuk kembali ke menu utama.",
                parse_mode="HTML"
            )

# ========== TOGGLE STATUS DAN TAMPILKAN DETAIL ==========
async def handle_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    tipe, name = query.data.split("|")

    # Support semua kategori (dayli, testnet, mining)
    current = user_tasks[user_id][tipe][name]["done"]
    user_tasks[user_id][tipe][name]["done"] = not current
    data = user_tasks[user_id][tipe][name]

    status = "✅ DONE" if not current else "❌ TODO"
    
    msg = f"""📌 <b>Tutorial: {name}</b>

🔗 <b>LINK WEB:</b> {data['web']}
🚰 <b>LINK FAUCET:</b> {data['faucet']}

📝 <b>Cara garap:</b>
{data['cara']}

Status: {status}
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Toggle Status", callback_data=f"toggle_{tipe}|{name}")],
        [InlineKeyboardButton("🔙 Kembali", callback_data=tipe)]
    ]
    
    await query.answer()
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# ========== HANDLE TOGGLE STATUS ==========
async def handle_status_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    _, data_part = query.data.split("_", 1)
    tipe, name = data_part.split("|")
    
    # Toggle status - support semua kategori (dayli, testnet, mining)
    current = user_tasks[user_id][tipe][name]["done"]
    user_tasks[user_id][tipe][name]["done"] = not current
    data = user_tasks[user_id][tipe][name]

    status = "✅ DONE" if not current else "❌ TODO"
    
    msg = f"""📌 <b>Tutorial: {name}</b>

🔗 <b>LINK WEB:</b> {data['web']}
🚰 <b>LINK FAUCET:</b> {data['faucet']}

📝 <b>Cara garap:</b>
{data['cara']}

Status: {status}
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Toggle Status", callback_data=f"toggle_{tipe}|{name}")],
        [InlineKeyboardButton("🔙 Kembali", callback_data=tipe)]
    ]
    
    await query.answer(f"Status berubah menjadi: {status}")
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# ========== JALANKAN BOT ==========
if __name__ == '__main__':
    TOKEN = "7658578409:AAGO04veR5vEMo3Bxh_mIoX9NyBNxXvcanI"  # GANTI DENGAN TOKEN BOT KAMU
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_toggle, pattern="^[a-zA-Z]+\\|"))
    app.add_handler(CallbackQueryHandler(handle_status_toggle, pattern="^toggle_"))
    app.add_handler(CallbackQueryHandler(handle_menu))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot sedang starting...")
    
    try:
        # Stop any existing polling first
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("🔄 Mencoba restart bot...")
        try:
            app.run_polling(drop_pending_updates=True)
        except Exception as e2:
            print(f"❌ Masih error: {str(e2)}")
            print("⚠️ Pastikan tidak ada bot instance lain yang berjalan!")
