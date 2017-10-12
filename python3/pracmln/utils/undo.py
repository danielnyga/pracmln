# Data Structures with Undoable Manipulations
#
# (C) 2011-2013 by Daniel Nyga (nyga@cs.uni-bremen.de)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

class Undoable(object):
    """
    Base class for all data structures that support  histories of
    manipulations for undoing changes. Supports the concept of epochs:
    An epoch denotes a subsequence of actions that can be undone in a batch. 
    """

    def __init__(self):
        self.actionStack = []
        
    def reset(self):
        """
        Undoes all actions until the initial state is reached.
        """
        while not self.isReset():
            self.undo()
            
    def isReset(self):
        """
        Returns True if there is no action to be undone, thus the
        dict is entirely reset.
        """
        return len(self.actionStack) == 0
    
    def undo(self):
        """
        Undoes the most recent undoable action. Ignores epochs.
        """
        if len(self.actionStack) == 0:
            raise Exception('There is nothing to be undone.')
        action = self.actionStack.pop()
#         while action is None and len(self.actionStack) > 0: 
#             action = self.actionStack.pop()
        if action is not None:
            action.undo()
        
    def epochEndsHere(self):
        """
        Mark the current epoch as ended with the most recent action.
        """
        self.actionStack.append(None) # None serves as a separator between epochs
        
    def undoEpoch(self):
        """
        Undo all changes back to the previous epoch.
        """
        if len(self.actionStack) == 0:
            raise Exception('There is nothing to be undone.')
        if self.actionStack[-1] is not None:
            raise Exception('Epochs must be terminated by a separator.')
        self.actionStack.pop()
        while len(self.actionStack) > 0:
            action = self.actionStack.pop()
            if action is None:
                self.actionStack.append(None) 
                return
            else:
                action.undo()
    
    def do(self, action, *args):
        """
        Executes the action and pushes it onto the stack of actions.
        *args is the arguments to the action.
        """
        self.actionStack.append(action)
        action.do(*args)

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Undoable Actions - General
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

class UndoableAction(object):
    """
    An abstract interface for wrapper classes implementing
    some doable/undoable actions.
    """
    def __init__(self, struct):
        self.struct = struct
    
    def do(self, **args):
        """
        Called when the action should be performed.
        """
        pass
        
    def undo(self):
        """
        Called when the action should be undone.
        """
        pass

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Undoable Actions - Lists
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        
class ListAppend(UndoableAction):
    
    def do(self, el):
        self.struct.list.append(el)
        
    def undo(self):
        self.struct.list.pop()
        
class ListExtend(UndoableAction):
    
    def do(self, seq):
        self.elCount = len(seq)
        self.struct.list.extend(seq)

    def undo(self):
        for _ in range(self.elCount):
            self.struct.list.pop()
    
class ListRemove(UndoableAction):
    
    def do(self, el):
        self.idx = self.struct.list.index(el)
        self.el = el
        self.struct.list.remove(el)
    
    def undo(self):
        self.struct.list.insert(self.idx, self.el)
        
class ListEmpty(UndoableAction):
    
    def do(self):
        self.oldList = self.struct.list
        self.struct.list = []
    
    def undo(self):
        self.struct.list = self.oldList


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Undoable Actions - BooleanSet
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

class BooleanSet(UndoableAction):
    
    def do(self, isTrue):
        self.value = self.struct.value
        self.struct.value = isTrue
        
    def undo(self):
        self.struct.value = self.value

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Undoable Actions - ListDict
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

class ListDictPut(UndoableAction):
    
    def do(self, key, el):
        self.key = key
        l = self.struct.d.get(key, None)
        if l is None:
            l = []
            self.struct.d[key] = l
        if el not in l:
            self.el = el
            l.append(el)
        else:
            self.el = None
        
    def undo(self):
        if self.el is None: return
        l = self.struct.d[self.key]
        l.pop()
        if len(l) == 0:
            del self.struct.d[self.key]
            
class ListDictExtend(UndoableAction):
    
    def do(self, key, elements):
        self.key = key
        l = self.struct.d.get(key, None)
        if l is None:
            l = []
            self.struct.d[key] = l
        self.len = 0
        for e in elements:
            if e not in l: 
                l.append(e)
                self.len += 1
        
    def undo(self):
        l = self.struct.d[self.key]
        for _ in range(self.len): l.pop()
        if len(l) == 0:
            del self.struct.d[self.key]
            
class ListDictSetItem(UndoableAction):
    
    def do(self, key, el):
        self.key = key
        if not key in self.struct.d:
            self.none = True
        else:
            self.none = False
        self.oldValue = self.struct.d.get(key, None)
        self.struct.d[key] = el
        
    def undo(self):
        if self.none:
            del self.struct.d[self.key]
        else:
            self.struct.d[self.key] = self.oldValue

class ListDictDelete(UndoableAction):
    
    def do(self, key):
        self.key = key
        self.el = self.struct.d[key]
        del self.struct.d[key]
        
    def undo(self):
        self.struct.d[self.key] = self.el
            
class ListDictRemove(UndoableAction):

    def do(self, key, el):
        self.key = key
        self.el = el
        l = self.struct.d[key]
        self.l = l
        self.idx = l.index(el)
        l.remove(el)
        if len(l) == 0:
            del self.struct.d[key]
            
    def undo(self):
        l = self.struct.d.get(self.key, None)
        if not self.key in self.struct.d:
            self.struct.d[self.key] = self.l
        self.l.insert(self.idx, self.el)

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Undoable Actions - Numbers
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

class Addition(UndoableAction):
    
    def do(self, value):
        self.struct.value += value
        self.addend = value
        
    def undo(self):
        self.struct.value -= self.addend
        
class Multiplication(UndoableAction):
    
    def do(self, value):
        self.struct.value *= value
        self.muliplicand = value
        
    def undo(self):
        self.struct.value /= self.multiplicand
    
class Assignment(UndoableAction):
    
    def do(self, value):
        self.oldValue = self.struct.value
        self.struct.value = value
        
    def undo(self):
        self.struct.value = self.oldValue

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Undoable Actions - Numbers
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

class SetReference(UndoableAction):
    
    def do(self, obj):
        self.oldObj = self.struct.obj
        self.struct.obj = obj
        
    def undo(self):
        self.struct.obj = self.oldObj

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Undoable Structures - Reference
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

class Ref(Undoable):
    
    def __init__(self, obj):
        Undoable.__init__(self)
        self.obj = obj
        
    def set(self, obj):
        self.do(SetReference(self), obj)
        
    def __str__(self):
        return str(self.obj)
        
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Undoable Structures - ListDict
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

class ListDict(Undoable):
    """
    A dictionary mapping to lists of items. The main difference to the 
    normal dicts is that the methods for putting an item to the dict
    automatically create the empty list, when an entry does not exist
    so far. Analogously, when removing a item, an possibly empty list
    is removed from the dict. Also supports a history of all operations 
    for undoing changes.
    """
    
    def __init__(self, dictionary=None):
        Undoable.__init__(self)
        if dictionary is None:
            self.d = {}
        else:
            self.d = dictionary
        self.iteritems = self.d.iteritems
        self.__iter__ = self.d.__iter__

    def __len__(self):
        return len(self.d)
        
    def __getitem__(self, key):
        """
        As opposed to the standard dict, this method returns None if
        there is no dict entry for key, instead of raising an exception.
        """
        return self.d.get(key, None)
    
    def get(self, key, default=None):
        return self.d.get(key, default)
    
    def __setitem__(self, key, value):
        a = ListDictSetItem(self)
        self.actionStack.append(a)
        a.do(key, value)
        
    def __delitem__(self, key):
        a = ListDictDelete(self)
        self.actionStack.append(a)
        
        
    def put(self, key, element):
        """
        Undoable putting action of an element to the list associated to
        the key. If the list doesn't exist, it's created.
        """
        self.do(ListDictPut(self), key, element)
        
    def extend(self, key, elements):
        """
        Extend the list associated to the key by the elements.
        """
        self.do(ListDictExtend(self), key, elements)
        
    def drop(self, key, element):
        """
        Undoable action for dropping an element from the list 
        associated to the key. If the list gets empty, it's being
        deleted from the dict.
        """
        self.do(ListDictRemove(self), key, element)
    
#     def __iter__(self):
#         return self.d.keys()
        
    def keys(self):
        return list(self.d.keys())
        
    def values(self):
        return list(self.d.values())
        
    def contains(self, key, element):
        """
        Checks if the element is the list associated with the key.
        """
        l = self[key]
        if l is None: return False
        else: return element in l
        
    def __str__(self):
        return str(self.d)

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Undoable Structures - Numbers
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

class Number(Undoable):
    """
    Represents a numeric value, which keeps track of all changes made to it.
    The changes can be undone. Example:
        n = Number(0) # initialization
        n += 2
        print n # will print "2"
        n.undo()
        print n # will print "0"
    Caution: since "=" cannot be overridden, assignments need to be made
    by calling n.set(x)
    """
    
    @staticmethod
    def __value(number):
        if isinstance(number, Number):
            return number.value
        elif type(number) is int or type(number) is float:
            return number
        
    def __init__(self, value):
        Undoable.__init__(self)
        self.value = value
    
    def set(self, number):
        """
        Assigns a new value to the variable.
        """
        self.do(Assignment(self), Number.__value(number))
    
    def __iadd__(self, other):
        self.do(Addition(self), Number.__value(other))
        return self
        
    def __isub__(self, other):
        self.do(Addition(self), -Number.__value(other))
        return self
        
    def __imul__(self, other):
        self.do(Multiplication(self), Number.__value(other))
        return self
    
    def __idiv__(self, other):
        self.do(Multiplication(self), 1/Number.__value(other))
        return self
    
    def __add__(self, other):
        return self.value + Number.__value(other)
    
    def __sub__(self, other):
        return self.value - Number.__value(other)
    
    def __mul__(self, other):
        return self.value * Number.__value(other)
    
    def __div__(self, other):
        return self.value / Number.__value(other)
    
    def __repr__(self):
        return str(self)
    
    def __str__(self):
        return str(self.value)

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Undoable Structures - Boolean
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

class Boolean(Undoable):
    """
    Boolean supporting undo operations.
    """
    
    def __init__(self, isTrue):
        Undoable.__init__(self)
        self.value = isTrue
        
    def set(self, isTrue):
        self.do(BooleanSet(self), isTrue)
                
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Undoable Structures - List
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

class List(Undoable):
    """
    List supporting undo operations.
    """
    
    def __init__(self, *args):
        Undoable.__init__(self)
        self.list = [x for x in args]
        self.__iter__ = self.list.__iter__
        self.__contains__ = self.list.__contains__
        
    def append(self, element):
        self.do(ListAppend(self), element)

    def extend(self, sequence):
        for el in sequence: self.append(el)

    def remove(self, element):
        self.do(ListRemove(self), element)
        
    def pop(self):
        self.remove(self[-1])
        
    def clear(self):
        self.do(ListEmpty(self))
    
    def index(self, item):
        return self.list.index(item)
    
    def __getitem__(self, index):
        return self.list[index]
    
    def __getslice__(self, i, j):
        return self.list[i:j]
    
#     def __iter__(self):
#         return iter(self.list)
    
#     def __contains__(self, item):
#         return item in self.list
    
    def __len__(self):
        return len(self.list)
    
    def __str__(self):
        return str(self.list)
    

# for testing purposes only
if __name__ == '__main__':
    
    # test the ListDict history and epochs
    d = ListDict()
    print(d)
    d.put('a', 1)
    print(d)
    d.put('a', 2)
    print(d)
    d.put('b', 4)
    print(d)
    d.put('b', 4)
    print(d)
    d.put('b', 4)
    print(d)
    d.put('b', 4)
    print(d)
    d.drop('a', 2)
    print(d)
    print(len(d))
    while not d.isReset():
        d.undo()
        print(d)
        
    l = List()
    l.append(1)
    l.append(2)
    l.clear()
    l.append(1)
    print(l)
    l.undo()
    l.undo()
    print(l)
    
    # test the Number history
    n = Number(0)
    for _ in range(10):
        n += 1
        print(n)
    while not n.isReset():
        n.undo()
        print(n)
        
    # test the Ref history
    r = Ref('Hello, world!')
    print(len(r.obj))
    print(r)
    l = [1,2,3]
    r.set(l)
    print(r.obj)
    r.undo()
    print(r)
    
    b = Boolean(False)
    b.set(True)
    b.set(True)
    b.set(False)
    print(b.value)
    while not b.isReset():
        b.undo()
        print(b.value)
   
        
        
        
        
        
        
        
        
