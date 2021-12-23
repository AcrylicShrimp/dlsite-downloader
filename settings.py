import json
import os


class _Option:
    def __init__(self, /, validator=None, initValue=None, required=False):
        if required and initValue is None:
            raise ValueError('required option should have initial value')

        if (validator is not None) and (initValue is not None) and (validator(initValue) is False):
            raise ValueError('initial value should be valid')

        self.validator = validator
        self.initValue = initValue
        self.required = required
        self.value = None


def _typeCheck(decltype):
    return lambda o: isinstance(o, decltype)


_optionMap = {
    # string options
    'username': _Option(validator=_typeCheck(str), initValue='YOUR_USERNAME_HERE', required=True),
    'password': _Option(validator=_typeCheck(str), initValue='YOUR_PASSWORD_HERE', required=True),
}

#######################################################################################################


def _generateInitialSetting(fileName):
    global _optionMap

    initDict = {name: option.initValue for name, option in _optionMap.items()}

    try:
        with open(fileName, 'w', encoding='utf-8') as settings_file:
            settings_file.write(json.dumps(initDict, indent=4))

        print('a settings.json file created :)')
        print('please open and edit it to proceed!')
        print()
    except:
        print('unable to create settings.json file :(')
        print('please contact to led789zxpp@naver.com')
        print()

#######################################################################################################


def loadSettings(fileName='settings.json') -> bool:
    global _optionMap

    if not os.path.isfile(fileName):
        _generateInitialSetting(fileName)
        return False

    try:
        with open('settings.json', encoding='utf-8') as settings_file:
            settings = json.load(settings_file)
    except:
        print('unable to load settings.json file :(')
        print('please contact to led789zxpp@naver.com')
        print()

        return False

    containsInvalidValue = False

    for key, value in settings.items():
        option = _optionMap.get(key)

        if option is None:
            jsonValue = json.dumps(value)
            print('undefined setting "{}" found. (value: {}) :/'.format(key, jsonValue))
            print('it is ignored and not stored in settings map...')
            print()
            continue

        if (option.validator is not None) and (option.validator(value) is False):
            jsonValue = json.dumps(value)
            print(
                'invalid setting "{}" found. (value: {}) :('.format(key, jsonValue))
            print('please refer to docs and correct the setting.')
            print('for more information, contact to led789zxpp@naver.com')
            print()

            containsInvalidValue = True
            continue

        option.value = value

    if containsInvalidValue:
        return False

    someOptionsMissing = False

    for name, option in _optionMap.items():
        if option.required and option.value is None:
            print('required setting "{}" not found. :('.format(name))
            print('please refer to docs and fill out the setting.')
            print('for more information, contact to led789zxpp@naver.com')
            print()

            someOptionsMissing = True

    if someOptionsMissing:
        return False
    else:
        return True


def getSettingsMap() -> dict:
    return {name: option.value for name, option in _optionMap.items()}
