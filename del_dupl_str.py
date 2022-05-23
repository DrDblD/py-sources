def del_dupl_input(func):
    path=input("path:\t")
    with open(file=path, mode="r") as file:
        list_str=func(file)

def del_dupl(stream):
    return list(set([i for i in stream.reads()]))
 
