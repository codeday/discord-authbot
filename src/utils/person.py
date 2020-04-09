def id_from_mention(mention):
    try:
        return int(mention.replace('<', '').replace('!', '').replace('>', '').replace('@', ''))
    except:
        return False
