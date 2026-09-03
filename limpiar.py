import sys

def remover_claude(message):
    # Elimina la línea del coautor tanto con salto de línea de Linux (\n) como de Windows (\r\n)
    message = message.replace(b"Co-authored-by: Claude <claude@anthropic.com>\r\n", b"")
    message = message.replace(b"Co-authored-by: Claude <claude@anthropic.com>\n", b"")
    return message
