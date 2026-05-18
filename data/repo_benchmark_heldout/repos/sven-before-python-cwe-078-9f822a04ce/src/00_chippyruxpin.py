def talk(myText):
    if( myText.find( "twitter" ) >= 0 ):
        myText += "0"
        myText = myText[7:-1]
        try:
	    myText = twitter.getTweet( myText )
	except:
	    print( "!!!ERROR: INVALID TWITTER CREDENTIALS. Please read README.md for instructions.")
            return
    
    os.system( "espeak \",...\" 2>/dev/null" ) # Sometimes the beginning of audio can get cut off. Insert silence.
    time.sleep( 0.5 )
    os.system( "espeak -w speech.wav \"" + myText + "\" -s 130" )
    audio.play("speech.wav")
    return myText
