import functools
import time

import requests
import json






#Декоратор "retry" - Максимум попыток - 3, время ожидания - +-2сек ()
def retry(max_attempt: int = 3, expectation: int = 2):
    def decor(func):
        @functools.wraps(func)
        def wraps(*args, **kwargs):
            rtry = 0

            while rtry < max_attempt:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    rtry += 1

                    if rtry < max_attempt:
                        print(f"Попытка номер - {rtry} не удалась. Ошибка - {e}")
                        time.sleep(expectation)

            raise Exception("Ошибка. Все попытки исчерпаны")
        return wraps
    return decor


#Основной код. *Стоит изучить Rich.*



