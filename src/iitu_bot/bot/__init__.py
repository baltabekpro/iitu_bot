"""Telegram bot module with RAG integration"""

import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
import google.generativeai as genai
from typing import Dict, List, Optional
from ..config import Config
from ..database import VectorDatabase

logger = logging.getLogger(__name__)

class IITUTelegramBot:
    """IITU Telegram bot with RAG capabilities"""
    
    def __init__(self):
        # Initialize bot and dispatcher
        self.bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
        self.dp = Dispatcher()
        
        # Initialize Gemini AI
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.ai_model = genai.GenerativeModel('gemini-pro')
        
        # Initialize vector database
        self.vector_db = VectorDatabase()
        
        # User sessions for retry logic
        self.user_sessions: Dict[int, Dict] = {}
        
        # Register handlers
        self._register_handlers()
        
        logger.info("IITU Telegram Bot initialized")
    
    def _register_handlers(self):
        """Register message handlers"""
        
        @self.dp.message(CommandStart())
        async def start_handler(message: Message):
            await self.handle_start(message)
        
        @self.dp.message(Command('help'))
        async def help_handler(message: Message):
            await self.handle_help(message)
        
        @self.dp.message(Command('return'))
        async def return_handler(message: Message):
            await self.handle_return(message)
        
        @self.dp.message(F.text)
        async def text_handler(message: Message):
            await self.handle_text(message)
    
    async def handle_start(self, message: Message):
        """Handle /start command"""
        welcome_text = """
🎓 Добро пожаловать в IITU Assistant!

Я — ваш персональный помощник для абитуриентов и студентов Международного университета информационных технологий (IITU).

Я могу помочь вам с:
• Информацией о факультетах и специальностях
• Процедурах поступления
• Расписании и учебных программах
• Контактной информации
• Новостях университета
• И многим другим!

Просто задайте свой вопрос, и я постараюсь дать вам точный и полезный ответ.

Используйте /help для получения дополнительной информации.
        """
        
        await message.answer(welcome_text)
        
        # Initialize user session
        self.user_sessions[message.from_user.id] = {
            'retry_count': 0,
            'last_query': None,
            'context': []
        }
    
    async def handle_help(self, message: Message):
        """Handle /help command"""
        help_text = """
📖 IITU Assistant - Справка

🔍 Как использовать бота:
• Задавайте вопросы на русском, казахском или английском языке
• Я отвечу на основе актуальной информации об IITU
• Если ответ не подходит, используйте команду /return для уточнения

🤖 Доступные команды:
/start - Начать работу с ботом
/help - Показать эту справку
/return - Переформулировать последний запрос (до 3 раз)

💡 Примеры вопросов:
• "Какие факультеты есть в IITU?"
• "Как поступить в университет?"
• "Расскажи о специальности IT"
• "Контакты приемной комиссии"

Если у вас есть вопросы или предложения, свяжитесь с администрацией IITU.
        """
        
        await message.answer(help_text)
    
    async def handle_return(self, message: Message):
        """Handle /return command for query refinement"""
        user_id = message.from_user.id
        
        if user_id not in self.user_sessions:
            await message.answer("Сначала задайте вопрос, чтобы я мог его переформулировать.")
            return
        
        session = self.user_sessions[user_id]
        
        if not session['last_query']:
            await message.answer("Нет предыдущего запроса для переформулировки.")
            return
        
        if session['retry_count'] >= Config.MAX_RETRIES:
            await message.answer("Достигнуто максимальное количество попыток переформулировки. Попробуйте задать вопрос по-другому.")
            return
        
        session['retry_count'] += 1
        
        # Refine the query using AI
        refined_query = await self.refine_query(session['last_query'], session['context'])
        
        await message.answer(f"🔄 Переформулирую ваш запрос (попытка {session['retry_count']})...")
        
        # Process the refined query
        await self.process_user_query(message, refined_query, is_refined=True)
    
    async def handle_text(self, message: Message):
        """Handle text messages"""
        user_query = message.text.strip()
        
        if not user_query:
            await message.answer("Пожалуйста, задайте ваш вопрос.")
            return
        
        # Initialize session if not exists
        user_id = message.from_user.id
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                'retry_count': 0,
                'last_query': None,
                'context': []
            }
        
        # Reset retry count for new query
        self.user_sessions[user_id]['retry_count'] = 0
        self.user_sessions[user_id]['last_query'] = user_query
        
        await self.process_user_query(message, user_query)
    
    async def process_user_query(self, message: Message, query: str, is_refined: bool = False):
        """Process user query with RAG"""
        try:
            # Show typing action
            await self.bot.send_chat_action(message.chat.id, 'typing')
            
            # Search in knowledge base
            search_results = self.vector_db.search(query, n_results=5)
            
            user_id = message.from_user.id
            session = self.user_sessions[user_id]
            
            if search_results and self.vector_db.is_relevant(query):
                # Generate response using RAG
                response = await self.generate_rag_response(query, search_results)
                
                # Add to context
                session['context'].append({
                    'query': query,
                    'response': response,
                    'source': 'rag'
                })
                
            else:
                # Generate general response
                response = await self.generate_general_response(query)
                
                # Add to context
                session['context'].append({
                    'query': query,
                    'response': response,
                    'source': 'general'
                })
            
            # Keep only last 5 interactions in context
            if len(session['context']) > 5:
                session['context'] = session['context'][-5:]
            
            await message.answer(response)
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            await message.answer("Извините, произошла ошибка при обработке вашего запроса. Попробуйте позже.")
    
    async def generate_rag_response(self, query: str, search_results: List[Dict]) -> str:
        """Generate response using RAG"""
        # Prepare context from search results
        context_chunks = []
        for result in search_results:
            content = result.get('content', '')
            metadata = result.get('metadata', {})
            source_info = f"Источник: {metadata.get('page_title', 'Неизвестно')}"
            context_chunks.append(f"{content}\n({source_info})")
        
        context = "\n\n---\n\n".join(context_chunks)
        
        prompt = f"""
        Ты — Ассистент для студентов и абитуриентов IITU. Твоя задача — отвечать на вопросы пользователей, используя предоставленную информацию.

        Правила ответа:
        1. Используй ТОЛЬКО информацию из предоставленного контекста
        2. Отвечай кратко и четко
        3. Если информации недостаточно, скажи об этом честно
        4. Сохраняй язык вопроса пользователя
        5. Будь вежливым и профессиональным
        6. Не добавляй лишних комментариев или пояснений

        Контекст из базы знаний IITU:
        {context}

        Вопрос пользователя: {query}

        Ответ:
        """
        
        try:
            response = self.ai_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error generating RAG response: {str(e)}")
            return "Извините, не удалось сформировать ответ на основе доступной информации."
    
    async def generate_general_response(self, query: str) -> str:
        """Generate general response when no relevant knowledge found"""
        prompt = f"""
        Ты — Ассистент для студентов и абитуриентов IITU. Пользователь задал вопрос, который не связан с базой знаний университета.

        Правила ответа:
        1. Отвечай в рамках своей роли как ассистент IITU
        2. Если вопрос не связан с университетом, вежливо направь к релевантным темам
        3. Будь кратким и профессиональным
        4. Сохраняй язык вопроса пользователя
        5. Предлагай обратиться к официальным источникам при необходимости

        Вопрос пользователя: {query}

        Ответ:
        """
        
        try:
            response = self.ai_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error generating general response: {str(e)}")
            return "Извините, я могу помочь только с вопросами, связанными с IITU. Обратитесь к официальному сайту iitu.edu.kz за дополнительной информацией."
    
    async def refine_query(self, original_query: str, context: List[Dict]) -> str:
        """Refine user query using AI"""
        context_text = ""
        if context:
            recent_context = context[-3:]  # Use last 3 interactions
            for item in recent_context:
                context_text += f"Запрос: {item['query']}\nОтвет: {item['response'][:200]}...\n\n"
        
        prompt = f"""
        Переформулируй пользовательский запрос, чтобы получить более точный ответ из базы знаний IITU.

        Исходный запрос: {original_query}

        Контекст предыдущих взаимодействий:
        {context_text}

        Создай улучшенную версию запроса, которая:
        1. Более конкретная и четкая
        2. Использует ключевые слова, связанные с IITU
        3. Учитывает контекст предыдущих вопросов
        4. Сохраняет язык оригинального запроса

        Переформулированный запрос:
        """
        
        try:
            response = self.ai_model.generate_content(prompt)
            refined = response.text.strip()
            logger.info(f"Query refined: '{original_query}' -> '{refined}'")
            return refined
        except Exception as e:
            logger.error(f"Error refining query: {str(e)}")
            return original_query
    
    async def start_polling(self):
        """Start bot polling"""
        logger.info("Starting IITU Telegram Bot...")
        await self.dp.start_polling(self.bot)
    
    async def stop(self):
        """Stop the bot"""
        await self.bot.session.close()
        logger.info("IITU Telegram Bot stopped")