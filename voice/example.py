numbers = [0, 1, 0, 3, 12]
pos = 0
for n in numbers:
    if n != 0:
        numbers[pos] = n
        pos +=1
numbers[pos:] = [0] * (len(numbers)-pos)
print(numbers)