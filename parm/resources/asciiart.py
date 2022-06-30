import colorama

PROG_NAME_ASCII = """
     ,---.    .--.  ,---.
     | .-.\  / /\ \ | .-.\  |\    /|
     | |-' )/ /__\ \| `-'/  |(\  / |
     | |--' |  __  ||   (   (_)\/  |
     | |    | |  |)|| |\ \  | \  / |
     /(     |_|  (_)|_| \)\ | |\/| |
    (__)                (__)'-'  '-'
"""

PROG_ICON_ASCII = """
⣿⣿⣿⣿⣿⣿⣿⣿⣿⡷⠳⠓⠑⠁⠀⠀⢈⢈⢈⠘⠑⠱⡳⡷⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⠷⠓⢀⣌⣬⡾⠇⠀⠀⠐⠳⠳⠳⡳⡷⣧⣎⢌⠘⠱⡷⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⠷⠁⣈⣾⠷⠓⠁⠀⠀⠀⠀⠀⠀⢀⢈⢈⢈⠀⠐⠱⡷⣮⢌⠐⡳⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⡿⠁⣈⣾⠷⠁⠀⠀⠀⠀⠀⠀⠀⠀⣠⣿⠳⠳⣳⣿⠀⠀⠀⠐⡳⣯⠌⠰⣷⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⠿⠀⣨⡿⠁⠀⠀⠀⢀⢈⢈⢈⢈⠈⠀⣰⣿⠀1⣰⣿⠀⠀⠀⠀⠀⠱⣿⢎⠐⣷⣿⣿⣿⣿⣿⣿⣿⣿
⡿⠀⣨⡿⠁⠀⠀⠀⠀⣰⠿⠑⠑⣱⣿⠀⠰⡷⡷⡷⣷⣿⡷⡷⡷⣿⠌⠀⠰⣿⠎⠐⣿⣿⣿⣿⣿⣿⣿⣿
⠇⢀⣿⠃⠀⠀⠀⠀⠀⣰⢏1⢈⣸⣿⢈⢈⢈⠈⠀⣰⣿⠀0⠀⣿⠏⠀⠀⣰⣿⠀⣰⣿⣿⣿⣿⣿⣿⣿
⠀⣰⣿⠀⠀⠀⠀⠀⠀⠐⠳⠳⠳⣳⣿⠳⠳⠳⣿⠎⠐⡷⡧⡦⡦⡷⠃⠀⠀⠀⣿⠏⠐⣿⣿⣿⣿⣿⣿⣿
⠀⣰⣿⠀⠀⠀⣀⣮⣮⣮⣮⣎⠀⣰⣿⠀0⢀⣿⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⠏⠀⣿⣿⣿⣿⣿⣿⣿
⠈⡰⣿⠈⠀⠀⣰⣿⠀1⣰⣿⠀⠐⡳⡷⡷⡷⠳⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣿⠁⣠⣿⣿⣿⣿⣿⣿⣿
⢏⠀⣷⢏⠀⠀⡰⣿⣮⣮⣾⣿⣮⣮⣮⣎⠈⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⠿⠀⣼⣿⣿⣿⣿⣿⣿⣿
⣿⠎⠐⣷⢎⠀⠀⠀⠀⠀⣰⣿⠁1⠀⣿⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⡿⠀⣨⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⢎⠐⣳⣏⠈⠀⠀⠀⡰⣿⣌⣌⣌⣿⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣾⠷⠀⣨⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣏⠈⠱⣷⣎⢌⠀⠀⠐⠑⠑⠑⠁⠀⠀⠀⠀⠀⠀⠀⠀⣈⣮⡷⠃⢀⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣎⢈⠑⡳⣷⣎⣌⢈⢈⠀⠀⠀⠀⠀⢈⢈⣌⣮⡿⠳⠁⣈⣬⡿⠓⠐⡳⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣯⣎⢌⠘⠑⠳⠳⡷⡷⡷⡷⠷⠳⠳⠑⢀⣈⣬⣾⣿⣿⣎⠈⣈⣾⠷⡳⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣮⣮⣎⣌⣌⣌⣬⣮⣮⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠉⣈⣾⠷⡳⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠉⠀⠀⠐⡳⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣎⠈⠀⠀⠐⣳
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣎⢈⠀⢀
"""

DEFAULT_NAME_COLOR = colorama.Fore.MAGENTA
DEFAULT_ICON_COLOR = colorama.Style.DIM + colorama.Fore.LIGHTRED_EX

color_by_char = {
    '0': colorama.Style.BRIGHT + colorama.Fore.LIGHTGREEN_EX,
    '1': colorama.Style.BRIGHT + colorama.Fore.LIGHTGREEN_EX
}

def get_asciiart(color=False):
    name = PROG_NAME_ASCII
    icon = PROG_ICON_ASCII
    if color:
        name = f"{DEFAULT_NAME_COLOR}{name}{colorama.Fore.RESET}"
        icon = "".join([f"{colorama.Style.RESET_ALL + color_by_char[c]}{c}{colorama.Style.RESET_ALL + DEFAULT_ICON_COLOR}"
                        if color_by_char.get(c) else c for c in icon])
        icon = f"{DEFAULT_ICON_COLOR}{icon}{colorama.Style.RESET_ALL}"
    return name + icon
