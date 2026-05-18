def add_user(username, password):
    encPass = crypt.crypt(password,"22")
    #subprocess escapes the username stopping code injection
    subprocess.call(['useradd','-G','docker,wheel','-p',encPass,username])
