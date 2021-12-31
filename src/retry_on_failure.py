
RETRY_COUNT = 3


def retry_on_failure(func):
    def wrapper(*args, **kwargs):
        for count in range(RETRY_COUNT):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print('an error occured: %s' % e)

                if count + 1 == RETRY_COUNT:
                    print('download failed.')
                    return False

                print('[count=%d] retrying.' % (count + 1))

    return wrapper
