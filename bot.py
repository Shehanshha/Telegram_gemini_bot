from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackContext
)
from telegram.constants import ChatAction
from config import Config
from database import Database
from gemini_helper import GeminiHelper
from web_search import WebSearch
from limiter import rate_limit
import logging
from datetime import datetime
import asyncio

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states and constants
WEBSEARCH_PROMPT = range(1)
GEMINI_TIMEOUT = 25  # Seconds before timing out

async def start(update: Update, context: CallbackContext):
    """Handle /start command and user initialization"""
    try:
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Get or create user
        db_user = Database.get_user(user.id)
        if not db_user:
            Database.create_user({
                "chat_id": user.id,
                "first_name": user.first_name,
                "username": user.username,
                "phone": None,
                "verified": False,
                "created_at": datetime.utcnow()
            })
            db_user = Database.get_user(user.id)

        if not db_user.get('verified'):
            await request_contact(update)
            return
            
        await show_main_menu(update, context)
    except Exception as e:
        logger.error(f"Start error: {e}")
        await update.message.reply_text("⚠️ Initialization failed. Please try again.")

async def request_contact(update: Update):
    """Show contact sharing keyboard"""
    try:
        contact_button = [[KeyboardButton("📱 Share Contact", request_contact=True)]]
        await update.message.reply_text(
            "🔐 Verification Required\n\n"
            "Please share your phone number to continue:",
            reply_markup=ReplyKeyboardMarkup(
                contact_button, 
                one_time_keyboard=True,
                resize_keyboard=True
            )
        )
    except Exception as e:
        logger.error(f"Contact request error: {e}")

async def contact_handler(update: Update, context: CallbackContext):
    """Handle received contact information"""
    try:
        user = update.effective_user
        phone_number = update.message.contact.phone_number
        
        Database.update_phone(user.id, phone_number)
        
        await update.message.reply_text(
            "✅ Verification successful!\n"
            "You can now access all features.",
            reply_markup=ReplyKeyboardRemove()
        )
        await show_main_menu(update, context)
    except Exception as e:
        logger.error(f"Contact handler error: {e}")
        await update.message.reply_text("⚠️ Verification failed. Please try again.")

async def show_main_menu(update: Update, context: CallbackContext = None):
    """Display main interactive keyboard"""
    try:
        menu_options = [
            ["💬 Ask Question", "🖼 Analyze Image"],
            ["🌐 Web Search", "📚 Chat History"],
            ["⚙️ Settings"]
        ]
        
        reply_markup = ReplyKeyboardMarkup(
            menu_options,
            resize_keyboard=True,
            input_field_placeholder="Select an option..."
        )
        
        if context:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Main Menu:",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "Main Menu:",
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Menu error: {e}")

@rate_limit
async def handle_text(update: Update, context: CallbackContext):
    """Handle all text messages with enhanced error handling"""
    try:
        user_input = update.message.text
        chat_id = update.effective_chat.id
        
        user = Database.get_user(chat_id)
        if not user or not user.get('verified'):
            await request_contact(update)
            return

        # Show typing indicator
        await context.bot.send_chat_action(
            chat_id=chat_id, 
            action=ChatAction.TYPING
        )

        # Handle menu options
        if user_input == "💬 Ask Question":
            await update.message.reply_text("Type your question:", reply_markup=ReplyKeyboardRemove())
            return  # Add conversation state if needed
            
        elif user_input == "🖼 Analyze Image":
            await update.message.reply_text("Send an image for analysis:", reply_markup=ReplyKeyboardRemove())
            return  # Add conversation state if needed
            
        elif user_input == "🌐 Web Search":
            await web_search_command(update, context)
            return
            
        elif user_input == "📚 Chat History":
            await show_chat_history(update)
            await show_main_menu(update, context)
            return
            
        elif user_input == "⚙️ Settings":
            await show_settings(update)
            await show_main_menu(update, context)
            return
            
        else:
            try:
                # Process with timeout
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        GeminiHelper().generate_text, 
                        user_input
                    ),
                    timeout=GEMINI_TIMEOUT
                )
                
                # Truncate long responses
                if len(response) > 4096:
                    response = response[:4000] + "\n... [truncated]"
                    
                Database.save_message(chat_id, user_input, response)
                await update.message.reply_text(
                    f"🤖 **Response**\n\n{response}",
                    parse_mode="Markdown"
                )
                
            except asyncio.TimeoutError:
                logger.error("Gemini response timeout")
                await update.message.reply_text("⌛ Response timed out. Please try again.")
            except Exception as e:
                logger.error(f"Gemini API error: {str(e)}")
                await update.message.reply_text("⚠️ Error processing request. Please try rephrasing.")

        await show_main_menu(update, context)

    except Exception as e:
        logger.error(f"Text handler error: {str(e)}")
        await update.message.reply_text("⚠️ Temporary service issue. Please try again later.")

async def show_chat_history(update: Update):
    """Show chat history"""
    try:
        history = Database.get_chat_history(update.effective_chat.id)
        if not history:
            await update.message.reply_text("📚 No chat history found")
            return

        response = "📚 Last 10 Conversations:\n\n"
        for idx, msg in enumerate(history, 1):
            response += f"{idx}. You: {msg['user_message']}\n"
            response += f"   Bot: {msg['bot_response'][:50]}...\n\n"
        
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"History error: {e}")
        await update.message.reply_text("⚠️ Error retrieving history")

async def show_settings(update: Update):
    """Show settings menu"""
    try:
        await update.message.reply_text(
            "⚙️ Settings:\n\n"
            "1. Change language\n"
            "2. Notification preferences\n"
            "3. Reset account\n\n"
            "Feature under development!"
        )
    except Exception as e:
        logger.error(f"Settings error: {e}")

@rate_limit
async def handle_image(update: Update, context: CallbackContext):
    """Handle image analysis requests"""
    try:
        chat_id = update.effective_chat.id
        user = Database.get_user(chat_id)
        
        if not user or not user.get('verified'):
            await request_contact(update)
            return
        
        await context.bot.send_chat_action(
            chat_id=chat_id,
            action=ChatAction.UPLOAD_PHOTO
        )
        
        photo = await update.message.photo[-1].get_file()
        image_bytes = await photo.download_as_bytearray()
        
        # Convert bytearray to bytes
        image_data = bytes(image_bytes)
        
        analysis = await asyncio.wait_for(
            asyncio.to_thread(
                GeminiHelper().analyze_image,
                image_data  # Pass bytes instead of bytearray
            ),
            timeout=GEMINI_TIMEOUT
        )
        
        if len(analysis) > 4096:
            analysis = analysis[:4000] + "\n... [truncated]"
        
        Database.save_image(chat_id, photo.file_id, analysis)
        await update.message.reply_text(
            f"🖼 **Analysis**\n\n{analysis}",
            parse_mode="Markdown"
        )
    except asyncio.TimeoutError:
        logger.error("Image analysis timeout")
        await update.message.reply_text("⌛ Image processing timed out. Please try again.")
    except Exception as e:
        logger.error(f"Image handler error: {str(e)}")
        await update.message.reply_text("⚠️ Error processing image")
    finally:
        await show_main_menu(update, context)

async def handle_websearch(update: Update, context: CallbackContext):
    """Process web search results with enhanced reliability"""
    try:
        query = update.message.text
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING
        )
        
        results = WebSearch.search(query)
        
        response = (
            f"🌐 **Results for '{query}'**\n\n"
            f"📝 Summary:\n{results['summary']}\n\n"
            f"🔗 Links:\n" + "\n".join(f"- {link}" for link in results['links'])
        )
        
        await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Web search handler error: {str(e)}")
        await update.message.reply_text("⚠️ Search service unavailable")
    finally:
        await show_main_menu(update, context)
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext):
    """Cancel current operation"""
    try:
        await update.message.reply_text("Operation cancelled")
        await show_main_menu(update, context)
    except Exception as e:
        logger.error(f"Cancel error: {e}")
    return ConversationHandler.END

async def error_handler(update: Update, context: CallbackContext):
    """Enhanced error handler"""
    logger.error(msg="Exception while handling update:", exc_info=context.error)
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ An error occurred. Please try again later."
        )
        await show_main_menu(update, context)
    except Exception as e:
        logger.error(f"Error handler error: {e}")

def main():
    """Initialize and run the bot"""
    try:
        application = ApplicationBuilder().token(Config.TELEGRAM_TOKEN).build()

        # Main conversation handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                WEBSEARCH_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_websearch)]
            },
            fallbacks=[CommandHandler('cancel', cancel)],
            allow_reentry=True
        )

        # Register handlers
        application.add_handler(conv_handler)
        application.add_handler(MessageHandler(filters.CONTACT, contact_handler))
        application.add_handler(MessageHandler(filters.PHOTO, handle_image))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        application.add_error_handler(error_handler)

        logger.info("Bot running successfully...")
        application.run_polling(
            poll_interval=0.5,
            timeout=10,
            drop_pending_updates=True
        )
    except Exception as e:
        logger.error(f"Fatal startup error: {e}")

if __name__ == "__main__":
    main()