"""
#####################################################################################################################

    Alice Feb 2022   ~   Bot Telegram for Wordle Leaderboard

#####################################################################################################################
"""

import              pickle
import              os
import              re
from telegram       import ReplyKeyboardMarkup, Update, ReplyKeyboardRemove
from telegram.ext   import Updater, CommandHandler, MessageHandler, Filters, messagehandler
from telegram.ext   import ConversationHandler, PicklePersistence


DEBUG               = True
LOG                 = True

TOKEN               = "5110592823:AAHt0lUu-BuE-5_z3XCDq1ZWEobvAiP5Ssc"  # unique bot ID
LNAME               = "leaderboard.pickle"                              # pickle file to store the list of cookies
ONAME               = "log.txt"                                         # log file

FAIL                = 8                                                 # penalty for not guessing the word
FAIL_s              = 'FAIL'                                            # string for not guessing the word
DAY_MALUS           = 0.20                                              # penalty for not playing a day
DAY_BONUS           = 0.05                                              # bonus for number of days played

pattern             = "^(Wordle [0-9]+ ([1-6]|X)/6)"                    # structure of the message generated by wordle
score_dict          = dict()                                            # dict with the users and their scores
last_day            = 0                                                 # last day of play



# ===================================================================================================================
#
#   Support functions
#
#   - msg
#   - img
#   - get_last_day
#   - check_user
#   - add_user
#   - add_score
#   - get_score
#
# ===================================================================================================================

def msg( update, txt, mrkp=None, parse='Markdown' ):
    """ -------------------------------------------------------------------------------------------------------------
    Make the bot send a message
    ------------------------------------------------------------------------------------------------------------- """
    update.message.reply_text( txt, reply_markup=mrkp, disable_web_page_preview=True, parse_mode=parse )


def img( update, img_url ):
    """ -------------------------------------------------------------------------------------------------------------
    Make the bot send an image
    ------------------------------------------------------------------------------------------------------------- """
    update.message.reply_photo( img_url )


def set_last_day():
    """ -------------------------------------------------------------------------------------------------------------
    Get the code of last game day
    ------------------------------------------------------------------------------------------------------------- """
    global last_day
    l = []

    for d in score_dict.values():
        l += list( d.keys() )

    last_day    = max( l )


def check_user( user, update ):
    """ -------------------------------------------------------------------------------------------------------------
    Check if user has @username
    ------------------------------------------------------------------------------------------------------------- """
    if user in ( None or 'None' ):
        txt     = "ERROR: you must have a Telegram username to play.\n"
        txt    += "You can set your username in the setting menu."
        msg( update, txt )
        return False
    return True


def add_user( user ):
    """ -------------------------------------------------------------------------------------------------------------
    Add a new user to the dict
    ------------------------------------------------------------------------------------------------------------- """
    score_dict[ user ]           = dict()


def add_score( user, day, score ):
    """ -------------------------------------------------------------------------------------------------------------
    Add user's score of the day
    ------------------------------------------------------------------------------------------------------------- """
    assert isinstance( day, int )
    assert ( isinstance( score, int ) ) or ( score == FAIL_s )

    if score == FAIL_s:
        score = FAIL

    score_dict[ user ][ day ]    = score


def get_score( user ):
    """ -------------------------------------------------------------------------------------------------------------
    Get average score of user
    ------------------------------------------------------------------------------------------------------------- """
    n   = len( score_dict[ user ] )                 # days played
    d   = min( score_dict[ user ].keys() )          # first day played

    if n > 0:
        m       = 0
        bonus   = DAY_BONUS * n
        malus   = DAY_MALUS * ( last_day - d + 1 - n )

        for v in score_dict[ user ].values():
            m   += FAIL if v == FAIL_s else v
        s   = m / n - bonus + malus                 # final score

        # if DEBUG:
            # print( f"{ user } scored { s }, with days { n }, mean { m/n }, bonus { bonus }, malus { malus }" )
        return round( s, 2 )
    return None



# ===================================================================================================================
#
#   Main conversation
#
#   - start_conv
#   - save_score
#   - show_lead
#   - show_stats
#   - show_help
#
# ===================================================================================================================

def start_conv( update, context ):
    """ -------------------------------------------------------------------------------------------------------------
    Start the conversation
    ------------------------------------------------------------------------------------------------------------- """
    user    = update.effective_user.username
    if not check_user( user, update ):
        return

    # markdown does not accept the _ symbol
    txt     = f"Ciao @{ user }"
    msg( update, txt, parse=None )

    txt     = "Play [Wordle](https://www.nytimes.com/games/wordle/index.html) and share your score! "
    txt    += "Check the /leaderboard or monitor your /stats. "
    txt    += "If you need help, type /help."
    msg( update, txt )



def save_score( update, context ):
    """ -------------------------------------------------------------------------------------------------------------
    Save the score of the day. User must send a message generated by the Wordle website
    ------------------------------------------------------------------------------------------------------------- """
    user        = update.effective_user.username
    if not check_user( user, update ):
        return

    sent_txt    = update.message.text
    r           = re.search( pattern, sent_txt )

    # received a message not conforming
    # this checks also if the score is in [1..6]
    if r is None:
        txt     = "ERROR: the bot only accepts messages generated by Wordle"
        msg( update, txt )
        return

    # get day and score
    day     = int( sent_txt.split( "\n" )[ 0 ].split()[ 1 ] )
    score   = sent_txt.split( "\n" )[ 0 ].split()[ -1 ][ 0 ]

    if user not in score_dict:
        add_user( user )

    if day in score_dict[ user ]:
        txt     = f"ERROR: @{ user } has already played this day."
        msg( update, txt, parse=None )
        return

    if score == 'X':
        score   = FAIL_s
    elif int( score ) == 1:                     # to prevent Gastone from cheating
        txt     = f"GASTONE SMETTILA"
        msg( update, txt )
        return
    else:
        score   = int( score )

    # add day and score to the dict
    add_score( user, day, score )

    # save the dict
    with open( LNAME, 'wb' ) as f:
        pickle.dump( score_dict, f, protocol=pickle.HIGHEST_PROTOCOL )

    if LOG:
        olog     = open( ONAME, 'a' )
        olog.write( f"Day { day }\t{ user }\tscore { score }\n" )
        olog.close()
    else:
        if DEBUG:   print( score_dict )
        else:       print( f">>> { user } saved score { score } for day { day }" )

    txt     = f"Saved @{ user } score of the day."
    msg( update, txt, parse=None )



def show_day_lead( update, context ):
    """ -------------------------------------------------------------------------------------------------------------
    Show the leaderboard of the day
    ------------------------------------------------------------------------------------------------------------- """
    if len( score_dict ) == 0:
        txt     = "No users have played yet."
        msg( update, txt )
        return

    txt         = f"\U0001F4C5 LEADERBOARD OF DAY { last_day }\n\n"
    lead_dict   = dict()

    # get users scores
    for user in score_dict:
        if last_day in score_dict[ user ]:
            lead_dict[ user ]   = score_dict[ user ][ last_day ]

    # sort the leaderboard
    sorting     = lambda x: ( x[ 1 ], x[ 0 ].lower() )
    lead_list   = [ ( k, v ) for k, v in sorted( lead_dict.items(), key=sorting ) ]

    # print the leaderboard
    for r, ( u, s ) in enumerate( lead_list, 1 ):
        if r == 1:
            medal   = "\U0001F947 "
        elif r == 2:
            medal   = "\U0001F948 "
        elif r == 3:
            medal   = "\U0001F949 "
        else:
            medal   = ''
        txt     += f"{ r }. { medal }@{ u } ({ s })\n"
    msg( update, txt, parse=None )



def show_avg_lead( update, context ):
    """ -------------------------------------------------------------------------------------------------------------
    Show the average leaderboard
    ------------------------------------------------------------------------------------------------------------- """
    if len( score_dict ) == 0:
        txt     = "No users have played yet."
        msg( update, txt )
        return

    txt         = "\U0001F3C6 GLOBAL LEADERBOARD\n\n"
    lead_dict   = dict()

    # get users scores
    for user in score_dict:
        lead_dict[ user ]   = get_score( user )

    # sort the leaderboard
    sorting     = lambda x: ( x[ 1 ], x[ 0 ].lower() )
    lead_list   = [ ( k, v ) for k, v in sorted( lead_dict.items(), key=sorting ) ]

    # print the leaderboard
    for r, ( u, s ) in enumerate( lead_list, 1 ):
        if r == 1:
            medal   = "\U0001F947 "
        elif r == 2:
            medal   = "\U0001F948 "
        elif r == 3:
            medal   = "\U0001F949 "
        else:
            medal   = ''
        txt     += f"{ r }. { medal }@{ u } ({ s }) [{ len( score_dict[ u ] ) }]\n"
    msg( update, txt, parse=None )



def show_leads( update, context ):
    """ -------------------------------------------------------------------------------------------------------------
    Show the leaderboards
    ------------------------------------------------------------------------------------------------------------- """
    set_last_day()
    show_day_lead( update, context )
    show_avg_lead( update, context )



def show_stats( update, context ):
    """ -------------------------------------------------------------------------------------------------------------
    Show personal stats
    ------------------------------------------------------------------------------------------------------------- """
    user        = update.effective_user.username
    if not check_user( user, update ):
        return

    if ( user not in score_dict ) or ( len( score_dict[ user ] ) == 0 ):
        txt    = "You haven't submit any score."
        msg( update, txt )
        return

    # get user stats
    val     = list( score_dict[ user ].values() )
    n_day   = len( score_dict[ user ] )

    txt     = "\U0001F4CA YOUR STATS\n\n"
    txt    += f"You played { n_day } game(s)\n"
    txt    += f"You guessed in *1* move { val.count( 1 ) } time(s)\n"
    txt    += f"You guessed in *2* moves { val.count( 2 ) } time(s)\n"
    txt    += f"You guessed in *3* moves { val.count( 3 ) } time(s)\n"
    txt    += f"You guessed in *4* moves { val.count( 4 ) } time(s)\n"
    txt    += f"You guessed in *5* moves { val.count( 5 ) } time(s)\n"
    txt    += f"You guessed in *6* moves { val.count( 6 ) } time(s)\n"
    txt    += f"You failed { val.count( FAIL_s ) } time(s)\n"
    msg( update, txt )



def show_help( update, context ):
    """ -------------------------------------------------------------------------------------------------------------
    Display the help message
    ------------------------------------------------------------------------------------------------------------- """
    txt     = "Play from the official [Wordle website](https://www.nytimes.com/games/wordle/index.html).\n"
    txt    += "From the website, share your score through Telegram directly to the bot.\n"
    msg( update, txt )
    img( update, "https://cdn.nerdschalk.com/wp-content/uploads/2022/01/002-9.png" )

    txt     = "Your score on the leaderboard is the average of all your games. "
    txt    += "The lower the score, the better. "
    txt    += f"If you fail to guess the word of the day, you get { FAIL } points. "
    txt    += f"For everyday you play, you get a bonus of { DAY_BONUS } points. "
    txt    += f"For everyday you don't play since you started, you get a penalty of { DAY_MALUS } points."
    msg( update, txt )



# ===================================================================================================================
#
#   MAIN
#
# ===================================================================================================================

def main():
    global score_dict

    if LOG:
        with open( ONAME, 'w' ) as olog:
            olog.write( ">>> BOT STARTED <<<\n" )
    else:
        print( ">>> BOT STARTED <<<" )

    # if exists, load the last pickled dict of leaderboard
    if os.path.isfile( LNAME ):
        with open( LNAME, "rb" ) as f:
            score_dict = pickle.load( f )

    set_last_day()

    updater         = Updater( TOKEN )
    dispatcher      = updater.dispatcher
    filter_mess     = Filters.text & ~( Filters.command )

    handl_start     = CommandHandler( 'start', start_conv )
    handl_mess      = MessageHandler( filter_mess, save_score )
    handl_lead      = CommandHandler( 'leaderboard', show_leads )
    handl_stats     = CommandHandler( 'stats', show_stats )
    handl_help      = CommandHandler( 'help', show_help )

    dispatcher.add_handler( handl_start )
    dispatcher.add_handler( handl_mess )
    dispatcher.add_handler( handl_lead )
    dispatcher.add_handler( handl_stats )
    dispatcher.add_handler( handl_help )

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
