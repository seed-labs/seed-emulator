class `Simulator`
---

Thought:

- Make a global "object registry." Basically, a Python dictionary that maps names to the corresponding object (`Network`, `Router`, `AS`, etc.) Since they all have different naming conventions, this should be fine.
- Move `<add/get>Host`/`<add/get>BGPRouter` to class `AS`. It makes the `Simulator` class cleaner. As long as we have the "object registry" as described above, we can always retrive the object with name.


