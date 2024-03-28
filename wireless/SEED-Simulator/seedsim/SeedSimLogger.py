import logging



# logger.warning('This is a warning')
# logger.error('This is an error')

class SeedSimLogger():
    
    # Create handlers
    c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler('file.log')
    c_handler.setLevel(logging.INFO)
    f_handler.setLevel(logging.DEBUG)

    # Create formatters and add it to handlers
    c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    # # Create a custom logger
    # logger = logging.getLogger()
    # logger.setLevel(level=logging.DEBUG)
    # # Add handlers to the logger
    # logger.addHandler(c_handler)
    # logger.addHandler(f_handler)

    @classmethod
    def debug(cls, clsname:str, msg:str):
        # Create a custom logger
        logger = logging.getLogger(clsname)
        logger.setLevel(level=logging.DEBUG)
        # Add handlers to the logger
        logger.addHandler(cls.c_handler)
        logger.addHandler(cls.f_handler)
        logger.debug(msg)

    @classmethod
    def info(cls, clsname:str, msg:str):
        # Create a custom logger
        logger = logging.getLogger(clsname)
        logger.setLevel(level=logging.DEBUG)
        # Add handlers to the logger
        logger.addHandler(cls.c_handler)
        logger.addHandler(cls.f_handler)
        logger.info(msg)