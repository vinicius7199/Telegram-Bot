import logging
import json
import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils import executor

# Configure logging
logging.basicConfig(level=logging.DEBUG)

API_TOKEN = 'API'  # Aqui deve ser inserido a chave do bot que irá configurar.


# Initialize bot and dispatcher
# bot = Bot(token=API_TOKEN, proxy="http://proxy.server:3128")      # pythonanywhere
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
with open('full.json', 'r') as f:
    full = json.load(f)

# For example use simple MemoryStorage for Dispatcher.
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# States
class Form(StatesGroup):
    apresentacao = State()      # storage as 'Form:apresentacao'
    nome = State()              # storage as 'Form:nome'
    opcao = State()             # storage as 'Form:opcao'
    continua = State()          # storage as 'Form:continua'


@dp.message_handler(commands=['info'])
async def send_welcome(message: types.Message):
    await message.reply("Hi! I'm NomesIBGEBot!\nPowered by:"
                        "\nMSPower\n")


@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    await types.ChatActions.typing(0.5)     # ação de 'digitando'

    # abre arquivo de usuários permitidos
    with open('user.txt') as file:
        userList = file.read()
    user = userList.split('\n')

    textomsg1 = ''
    if message['chat']['username']:
        textomsg1 += message["chat"]["username"]
        with open('logs.log', 'a') as arquivo:
            arquivo.write('\n' + message["chat"]["username"] + '\n\n')
        if textomsg1 in user:
            # entrada para a conversa
            # Set state
            await Form.apresentacao.set()

            # Configure ReplyKeyboardMarkup
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
            markup.add("Sim", "Não")
            await message.reply("Antes de pesquisar, siga as regras para encontrar as informações do nome:\n\n"
                                "1 - Informe apenas o primeiro nome;\n"
                                "2 - O nome não deve conter números;\n"
                                "3 - Escreva um nome aprovado pelo IBGE;\n"
                                "4 - O nome não deve conter caracteres especiais como pontos ou traços.\n"
                                "\nVocê concorda com as regras acima?", reply_markup=markup)

        else:
            await message.answer("No momento você não possui permissão para acessar as informações internas.\n"
                                 "Entre em contato com os desenvolvedores.\n"
                                 "Para mais informações dos meu criadores digite '/info'")
    else:
        await message.answer('Olá ' + message['chat'][
            'first_name'] + ', no momento não encontrei seu username.'
                            'Você deve verificá-lo nas configurações do Telegram.')


# You can use state '*' if you need to handle all states
@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    # permite cancelar a ação
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info('Cancelling state %r', current_state)
    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await message.reply('Cancelled.', reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(state=Form.apresentacao)
async def process_name(message: types.Message, state: FSMContext):
    await types.ChatActions.typing(0.3)     # ação de 'digitando'

    # processa username
    async with state.proxy() as data:
        data['apresentacao'] = message.text.lower()

        # Remove keyboard
        markup = types.ReplyKeyboardRemove()

        if data['apresentacao'] != "sim":
            await message.reply("<b>Busca encerrada.</b> Para iniciar a busca novamente digite:"
                                 "\n'/start'", reply_markup=markup, parse_mode=ParseMode.HTML)
            await state.finish()    # interrompendo ação
        else:
            await Form.next()       # próximo State
            await message.reply("Qual nome você gostaria de pesquisar?", reply_markup=markup)


# confere o nome
@dp.message_handler(lambda message: message.text.isdigit(), state=Form.nome)
async def process_nome_invalid(message: types.Message):
    await types.ChatActions.typing(0.5)     # ação de 'digitando'

    return await message.reply("Você deve fornecer um nome.\nQual nome você gostaria de pesquisar?")


@dp.message_handler(lambda message: message.text, state=Form.nome)
async def process_nome(message: types.Message, state: FSMContext):
    await types.ChatActions.typing(0.5)     # ação de 'digitando'

    # Update state and data
    await Form.next()
    await state.update_data(nome=(message.text.upper()))

    # Configure ReplyKeyboardMarkup
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add("Nome e Variações", "Gênero")
    markup.add("Frequência Feminina", "Frequência Masculina")
    markup.add("Frequência Total")
    markup.add("Explique os conceitos")

    await message.reply("Qual informação você deseja de saber?", reply_markup=markup)


@dp.message_handler(
    lambda message: message.text not in ["Nome e Variações", "Gênero", "Frequência Feminina", "Frequência Masculina",
                                         "Frequência Total", "Explique os conceitos"], state=Form.opcao)
async def process_opcao_invalid(message: types.Message):
    await types.ChatActions.typing(0.5)     # ação de 'digitando'

    return await message.reply("Escolha mal sucedida, por favor utilize o teclado.")


@dp.message_handler(state=Form.opcao)
async def process_opcao(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        await types.ChatActions.typing(0.3)     # ação de 'digitando'

        data['info'] = message.text
        segundos = message['date']
        with open('logs.log', 'a') as arquivo:
            arquivo.write(segundos.__str__())

        with open('user.txt') as file:
            userList = file.read()
        user = userList.split('\n')

        textomsg = ''
        if message["chat"]["username"]:
            textomsg += message["chat"]["username"]
            with open('logs.log', 'a') as arquivo:
                arquivo.write('\n' + message["chat"]["username"] + '\n\n')
        else:
            await message.answer("Você não possui um Username. Logo, deverá ir em suas configurações e nomeá-lo.")

        data['opcao'] = message.text    # mensagem do usuário

        # explica conceitos das opções
        if data['opcao'] == "Explique os conceitos":
            await types.ChatActions.typing(0.2)  # ação de 'digitando'
            await message.answer("<b>Nome e Variações:</b> mostra o nome e suas variações reconhecidas pelo IBGE;", parse_mode=ParseMode.HTML)
            await types.ChatActions.typing(0.2)  # ação de 'digitando'
            await message.answer("<b>Gênero:</b> mostra o gênero que o IBGE considera o nome;", parse_mode=ParseMode.HTML)
            await types.ChatActions.typing(0.2)  # ação de 'digitando'
            await message.answer("<b>Frequência Feminina:</b> informa a frequência que mulheres possuem esse nome;", parse_mode=ParseMode.HTML)
            await types.ChatActions.typing(0.2)  # ação de 'digitando'
            await message.answer("<b>Frequência Masculina:</b> informa a frequência que homens possuem esse nome;", parse_mode=ParseMode.HTML)
            await types.ChatActions.typing(0.2)  # ação de 'digitando'
            await message.answer("<b>Frequência Total:</b> informa a frequência que pessoas possuem esse nome;", parse_mode=ParseMode.HTML)
            await types.ChatActions.typing(0.2)  # ação de 'digitando'
            await message.answer("<b><i>Informe a opção desejada.</i></b>", parse_mode=ParseMode.HTML)
            return
        # pesquisa nome no dicionário
        elif textomsg in user:
            full
            txt = ''
            for n in full:
                if data['nome'] in n['nome']:
                    if data['opcao'] == "Nome e Variações":
                        if n['nome']:
                            txt += f'<b>Nome e Variações: </b> <i>{n["nome"]}</i>\n'
                    if data['opcao'] == "Gênero":
                        if n['genero']:
                            txt += f'<b>\nGênero: </b> <i>{n["genero"]}</i>\n'
                    if data['opcao'] == "Frequência Feminina":
                        if n['frequnciaF']:
                            txt += f'<b>\nFrequência Feminina: </b> <i>{n["frequnciaF"]}</i>\n'
                    if data['opcao'] == "Frequência Masculina":
                        if n['frequnciaM']:
                            txt += f'<b>\nFrequência Masculina: </b> <i>{n["frequnciaM"]}</i>\n'
                    if data['opcao'] == "Frequência Total":
                        if n['frequnciaT']:
                            txt += f'<b>\nFrequência Total: </b> <i>{n["frequnciaT"]}</i>\n'

            # Remove keyboard
            markup = types.ReplyKeyboardRemove()
            await message.answer("<i>Pesquisando...</i>", parse_mode=ParseMode.HTML)
            await types.ChatActions.typing(0.3)  # ação de 'digitando'
            await bot.send_message(message.chat.id,
                                   md.text(
                                       md.bold("Nome: "), md.italic(data['nome']),
                                       md.bold("\nOpção selecionada: "), md.italic(data['opcao'])),
                                   reply_markup=markup, parse_mode=ParseMode.MARKDOWN)

            if txt != "":
                await types.ChatActions.typing(0.2)  # ação de 'digitando'
                await bot.send_message(message.chat.id, txt, parse_mode=ParseMode.HTML)

            elif message.text.isdigit() == False:
                await types.ChatActions.typing(0.2)  # ação de 'digitando'
                await message.answer("Nome não encontrado.")
                await state.finish()

            # Update state and data
            await Form.next()
            await state.update_data(continua=(message.text.upper()))

            # Configure ReplyKeyboardMarkup
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
            markup.add("Novas informações")
            markup.add("Novo nome")
            markup.add("Encerrar busca")

            await message.reply("O que deseja fazer agora?", reply_markup=markup)

    # Finish conversation
    # await state.finish()


@dp.message_handler(lambda message: message.text not in ["Novas informações", "Novo nome", "Encerrar busca"],
                    state=Form.continua)
async def process_continua_invalid(message: types.Message):
    await types.ChatActions.typing(0.5)     # ação de 'digitando'

    return await message.reply("Escolha mal sucedida, por favor utilize o teclado.")


@dp.message_handler(state=Form.continua)
async def process_continua(message: types.Message, state: FSMContext):
    await types.ChatActions.typing(0.1)     # ação de 'digitando'
    markup = types.ReplyKeyboardRemove()

    async with state.proxy() as data:
        data['continua'] = message.text

        if data['continua'] == "Novas informações":
            await Form.previous()  # State nome
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
            markup.add("Nome e Variações", "Gênero")
            markup.add("Frequência Feminina", "Frequência Masculina")
            markup.add("Frequência Total")
            markup.add("Explique os conceitos")
            await message.answer("Qual informação você deseja?", reply_markup=markup)
        elif data['continua'] == "Novo nome":
            await Form.previous()
            await Form.previous()
            markup = types.ReplyKeyboardRemove() # Remove keyboard
            await message.answer("Qual nome você quer pesquisar?", reply_markup=markup)
        elif data['continua'] == "Encerrar busca":
            await message.answer("<b>Busca encerrada.</b> Para iniciar a busca novamente digite:"
                                "\n'/start'", reply_markup=markup, parse_mode=ParseMode.HTML)
            await state.finish()  # interrompendo ação


# echo para qualquer mensagem no início do bot
@dp.message_handler()
async def echo(message: types.Message):
    await types.ChatActions.typing(0.5)     # ação de 'digitando'

    # adiciona botão start
    entradas = ['oi', 'olá', 'oie', 'roi', 'hey', 'eai', 'eae', 'salve', 'hello', 'ei', 'hi', 'oii', 'oiee']

    if message.text.lower() in entradas:
        await message.answer('Olá ' + message['chat'][
            'first_name'] + ', eu sou o Bot de consulta, criado para encontrar as informações gerais de um nome.\n')

    if message.text != '':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
        markup.add("/start")
        await message.reply("Clique no botão '/start' para iniciar.",reply_markup=markup, parse_mode=types.ParseMode.HTML)

# final
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
