from os import environ

"""!
@brief This function returns to us the value of the saveState variable
If the build is done manually (environment variable not set), set saveState to True.
If the build is automated (environment variable set), set saveState to whatever is set in driver.sh
"""

def getSaveState(source:str = "") -> bool:
    print("=========== Calling getSaveState from " + source)

    env = environ.get('SAVE_STATE')
    
    print("=========== initial value retrieved is " + str(env))

    if env == None:
        state = True
    else:
        state = True if env == "True" else False

    print("=========== getSaveState returning " + str(state))
    return state
