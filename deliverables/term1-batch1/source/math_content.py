"""Rebuilt emergency mathematics content; deterministic worked tasks, not a curriculum certification."""
from fractions import Fraction as F
from decimal import Decimal, ROUND_HALF_UP
from math import gcd,lcm,isqrt
import random

MODULES={}
def add(key,title,notes,activity,error):
    MODULES[key]={'title':title,'notes':notes.split('|'),'activity':activity,'error':error}
add('place','Place value and expanded form','Our system is base ten. Ten units in one place exchange for one unit in the next place to the left.|The digit 3 in 43,216 has value 3,000. Face value and place value are different.|Expanded form shows a sum of place values: 43,216 = 40,000 + 3,000 + 200 + 10 + 6.|Zero holds an empty place. Removing the zero from 40,216 changes the number.','Build numbers with digit cards on a place-value chart. Exchange two digits and explain the change.','Do not confuse the digit itself with the value of the place it occupies.')
add('words','Reading and writing large numbers','Group digits in threes from the right: ones, thousands, millions and billions.|Read each non-zero group, followed by its scale name.|When writing figures from words, put zeros in the places not named.|Six hundred and three thousand and eight is 603,008. Read the result back to check it.','Partners dictate numbers and write figures, checking every place on a chart.','Do not write 603,800 for six hundred and three thousand and eight.')
add('chart','Number charts and counting steps','A number chart has a stated number of columns and a regular step along each row.|In a ten-column chart counting in ones, moving right adds 1 and moving down adds 10.|Moving left or up reverses the appropriate change.|If the chart counts in tens, a ten-column downward move adds 100. Always check both width and step.','Draw a five-by-ten chart. Cover entries and reconstruct them from neighbouring numbers.','A downward move does not always add 10; the width and counting step determine the change.')
add('compare','Comparing and ordering whole numbers','Compare the greatest place first. A positive whole number with more digits is larger.|For equally long numbers, compare left to right until the first unequal digit.|The open side of > or < faces the larger quantity. The symbol = means equal value.|Ascending order is least to greatest; descending order is greatest to least.','Sort number cards and explain which place decides each comparison.','A number containing the largest individual digit is not necessarily the largest number.')
add('round','Rounding whole numbers','Name the place to which the number is being rounded.|Inspect the digit immediately to its right: 0–4 keep the target digit; 5–9 increase it by one for nearest rounding.|Replace lower whole-number places with zeros. Check between neighbouring multiples on a number line.|Rounding to the nearest value is different from always rounding upward or downward.','Place numbers between neighbouring multiples of ten, a hundred or a thousand.','Do not remove place-holding zeros from a rounded whole number.')
add('skip','Skip counting','Skip counting adds or subtracts a fixed step repeatedly.|Find the difference between neighbouring terms before extending a sequence.|Check a missing middle term against the numbers on both sides.|Crossing a hundred or thousand boundary does not change the counting step.','Mark equal jumps on a number line and explain both forward and backward patterns.','Keep the interval constant rather than copying a pattern in only the last digit.')
add('roman','Roman numerals','I=1, V=5, X=10, L=50 and C=100.|Usually values are added from left to right. Permitted subtractive pairs include IV=4, IX=9, XL=40 and XC=90.|Write the largest values first, using standard forms: XXIV is 24.|Roman numerals do not use a place-value zero.','Use letter cards to build numbers and convert them back to ordinary figures.','Use IX, not VIIII, for 9; use XL, not XXXX, for 40.')
add('factors','Factors, primes and even numbers','A factor divides a positive whole number exactly, with no remainder.|Find factor pairs systematically: 18 has pairs 1×18, 2×9 and 3×6.|A prime number has exactly two positive factors. A composite has more than two; 1 is neither.|An even number is divisible by 2. The only even prime is 2.','Arrange counters into rectangles and record every factor pair.','Do not confuse a factor with a multiple. A positive factor cannot exceed the number.')
add('hcf','Highest common factor','List the factors of the given numbers or use their prime factors.|Common factors occur in every list. The HCF is the greatest positive common factor.|With prime factors, use shared primes with their smallest powers.|The HCF can determine the largest equal grouping that leaves nothing over.','Make identical packs from two colours of counters and identify the largest possible number of packs.','Do not choose the lowest common multiple when the question asks for a factor.')
add('lcm','Lowest common multiple','Multiples of a number are obtained by multiplying it by whole numbers.|List positive multiples of the given numbers; the first shared one is their LCM.|The LCM is useful for repeated events and common fraction denominators.|Zero is a common multiple but is not used as the least positive common multiple in these questions.','Draw two jump sequences on one number line and find their first shared positive landing point.','The HCF divides both numbers; the LCM is divisible by both numbers.')
add('facts','Multiplication facts and related division','Multiplication describes equal groups: 7×8 is seven groups of eight.|The commutative property gives 8×7=56 from 7×8=56.|Related division facts are 56÷7=8 and 56÷8=7.|Use arrays, doubling and known facts to derive an unfamiliar fact.','Build arrays with counters and write two multiplication and two division statements.','Seven groups of eight is not 7+8.')
add('multiply','Multiplication strategies','Partition a factor and use the distributive property: 24×6=(20×6)+(4×6)=144.|Doubling one factor and halving an even other factor preserves the product.|In multi-digit multiplication, include every partial product and align place values.|Estimate first, calculate carefully and compare the product with the estimate.','Draw a partitioned rectangle and connect its smaller areas to the partial products.','The tens digit contributes tens, not units: the 2 in 23×14 represents 20×14.')
add('divide','Division and checking','Division may mean sharing equally or finding how many equal groups fit.|Multiplication reverses division: 7×8=56 means 56÷7=8.|Work from the greatest place and regroup when needed. Record a zero in an empty quotient place.|Check: divisor × quotient + remainder = dividend. The remainder is smaller than the divisor.','Share counters into equal groups and check the result by multiplication.','Do not leave an empty place in the quotient when a zero is needed.')
add('word','Multi-step number problems','Identify the quantities, units and the final question before calculating.|Use a diagram or a written plan to select the operations from the relationships.|Label intermediate answers, then complete the remaining steps.|Estimate and interpret the answer in the original situation.','Use a shop-stock or shopping story. Draw a bar model and compare two solution methods.','A correct intermediate calculation may not answer the final question.')
add('integer','Positive and negative integers','Integers include negative whole numbers, zero and positive whole numbers.|On a number line, numbers increase to the right.|Adding a positive amount moves right; subtracting a positive amount moves left.|Use changes in balances or temperature to interpret signed quantities.','Walk along a floor number line to show addition and subtraction.','-8 is less than -3 even though 8 is greater than 3.')
add('unit','Unit fractions and number lines','A fraction names equal-sized parts of a whole.|The denominator counts equal parts and the numerator counts selected parts.|A unit fraction has numerator 1. Divide the interval from 0 to 1 into equal spaces, not an equal number of tick marks.|For the same whole, a larger denominator makes a unit fraction smaller.','Fold equal paper strips into halves, quarters and eighths, then mark the fractions on a number line.','Unequal pieces cannot be counted as equal fractions of the same whole.')
add('equiv','Equivalent fractions','Equivalent fractions have the same value even though their numerators and denominators differ.|Multiply or divide the numerator and denominator by the same non-zero number.|For example, 2/3=4/6=6/9. The amount stays the same.|Common denominators help compare or add fractions.','Shade equal lengths on strips partitioned into thirds and sixths.','Adding the same number to the numerator and denominator does not generally preserve value.')
add('simplify','Simplest form and improper fractions','A fraction is simplest when its numerator and denominator have no common factor greater than 1.|Divide both terms by their HCF: 12/18=2/3.|An improper fraction has numerator at least as large as denominator and represents at least one whole.|Divide the numerator by denominator to form a mixed number: the remainder becomes the new numerator.','Build more than one whole with fraction strips and record improper and mixed forms.','An improper fraction is not an incorrect fraction; it is a valid representation.')
add('fraccompare','Comparing fractions','Fractions must refer to the same-sized whole for a fair comparison.|With the same denominator, compare numerators. With the same numerator, a smaller positive denominator gives a larger fraction.|For unlike denominators, convert to a common denominator.|Use 0, 1/2 and 1 as benchmarks to check an ordering.','Place fraction cards on a number line and justify each position.','A larger denominator does not by itself mean a larger fraction.')
add('fracadd','Adding and subtracting fractions','Use a common denominator so the parts being combined are equal-sized.|Add or subtract the numerators and keep the common denominator.|For example, 1/2+1/3=3/6+2/6=5/6.|Convert mixed numbers to improper fractions if helpful, simplify and check against an estimate.','Repartition fraction strips into matching units before combining or taking away parts.','Do not add denominators: 1/2+1/3 is not 2/5.')
add('fracmul','Multiplying fractions and finding a fraction of a quantity','A fraction of a quantity means multiplication.|For example, 3/4 of 20 = (20÷4)×3 = 15.|Multiply fractions by multiplying numerators and denominators; simplify before or after multiplying.|Multiplying a positive quantity by a fraction between 0 and 1 makes it smaller.','Use counters for a fraction of a set and a shaded rectangle for a fraction of a fraction.','Multiplication does not always make the quantity larger.')
add('percent','Percentages','Percent means per hundred: 25%=25/100=1/4.|Find a percentage of a quantity by multiplying by the percentage divided by 100.|Useful benchmarks are 50%=1/2, 25%=1/4, 10%=1/10 and 75%=3/4.|For a discount, find the reduction and subtract it from the original price.','Use a 100-square and shop price cards to model percentages and discounts.','The discount amount is not the final selling price.')
add('mixed','Fractions, decimals and percentages','A fraction, a decimal and a percentage can represent the same quantity.|Divide numerator by denominator for a decimal. Multiply the decimal by 100 for a percent value.|Benchmarks include 1/2=0.5=50%, 1/4=0.25=25% and 3/4=0.75=75%.|Convert to a common form before ordering mixed representations.','Match fraction, decimal and percentage cards and place them on a number line.','0.5 is 50%, not 5%.')
add('ratio','Ratios in simplest form','A ratio compares quantities in a stated order.|The ratio 8:12 simplifies to 2:3 by dividing both terms by 4.|Multiply or divide every term by the same non-zero number to preserve the ratio.|In a part-to-part ratio 2:3, the first part is 2/5 of the total, not 2/3.','Compare groups of two colours of counters, then distinguish part-to-part from part-to-whole ratios.','Reversing the order of the quantities reverses the ratio.')
add('ratioeq','Equivalent ratios','Equivalent ratios describe the same relative amounts.|Multiply or divide all terms by the same positive number: 2:3=4:6=10:15.|Compare ratios using common second terms or equivalent fractions.|Equivalent ratios may describe groups with different totals.','Build a ratio table with counters, scaling both colours together.','Changing only one term generally changes the ratio.')
add('proportion','Direct proportion','Two quantities are directly proportional when their ratio stays constant.|Find the amount for one unit, then scale to the required number of units.|If 3 notebooks cost GH₵18, one costs GH₵6 and five cost GH₵30 at the same unit price.|A direct-proportion table contains equivalent ratios and pairs zero with zero.','Make a table of item counts and costs at a fixed price per item.','Two quantities increasing together does not by itself prove direct proportion.')
add('rates','Rates and scale','A rate compares quantities with different units, such as Ghana cedis per notebook.|Divide the total amount by the number of units to find a unit rate.|A map scale links a map measurement with a real-world distance.|Keep units explicit and reverse the calculation to check the result.','Measure distances on a drawn map using a stated scale.','Do not confuse centimetres on a map with kilometres in the real world.')
add('decimalround','Rounding decimals','Decimal places count digits to the right of the decimal point.|To round to tenths inspect hundredths; to round to hundredths inspect thousandths.|Retain the required number of decimal places, including a trailing zero when needed to show precision.|A carry may cross the decimal point: 9.96 to one decimal place is 10.0.','Place decimals between neighbouring tenths or hundredths on a number line.','Round directly to the requested place instead of rounding in several stages.')
add('sigfig','Significant figures','Significant figures start with the first non-zero digit.|Leading zeros do not count; zeros between significant digits do count.|Keep the requested number of significant digits and use the next digit to round.|0.00476 to two significant figures is 0.0048; 47,600 to two significant figures is 48,000.','Highlight the first significant digit, then count and mark the rounding place.','Significant figures and decimal places are different measures of precision.')
add('ten','Multiplying and dividing by powers of ten','Multiplying by 10, 100 or 1,000 increases each digit’s place value by that factor.|Dividing reverses the place-value shift.|4.26×100=426, while 4.26÷100=0.0426.|Use a place-value chart; appending zeros to a decimal is not a general multiplication rule.','Move digit cards on a chart including tenths, hundredths and thousandths.','4.260 has the same value as 4.26; it is not ten times as large.')
add('decimalops','Whole-number and decimal operations','Align decimal points when adding or subtracting decimals.|For multiplication, track the factors’ place values and check with an estimate.|For division, an equivalent calculation with an integer divisor may be useful.|State money answers with their currency; two decimal places are normally used for amounts in cedis.','Calculate receipts and totals from a price list, comparing exact answers with estimates.','Aligning final digits instead of decimal points changes the place values.')
add('powers','Powers and repeated factors','A power writes repeated multiplication: 3^4=3×3×3×3=81.|The base is the repeated factor; the exponent counts occurrences.|For a non-zero base, power zero equals 1.|A power is not multiplication by its exponent: 3^4 is not 3×4.','Build square arrays or repeated-factor diagrams and write matching index notation.','The zero-exponent rule here requires a non-zero base; do not apply it to 0^0.')
add('primepower','Prime factorisation and HCF','Prime factorisation expresses a whole number as a product of primes.|Repeated factors can be written as powers: 72=2^3×3^2.|For the HCF, multiply shared primes using the fewest copies occurring in any of the given numbers.|Multiply the factors back together to check the factorisation.','Draw factor trees for two numbers and circle their shared prime factors.','End a factor-tree branch only at a prime; 1 is not prime.')
add('standard','Standard form','Standard form for a positive number is a×10^n, where 1≤a<10 and n is an integer.|4,500,000=4.5×10^6; the exponent is positive for this large number.|0.0045=4.5×10^-3; the negative exponent represents division by a power of ten.|Convert back to ordinary notation to check coefficient and exponent.','Use a place-value chart to count the shifts needed for standard form.','45×10^5 has the right value for 4,500,000 but its coefficient is outside the standard-form range.')
add('sets','Sets, union, intersection and squares','A set is a collection of distinct elements; list each element once.|The union contains elements in either set. The intersection contains only elements in both.|A square number is an integer multiplied by itself; its non-negative square root reverses the operation.|In a Venn diagram, shared elements go in the overlap.','Sort numbered cards into overlapping hoops and record the union and intersection.','Do not count shared elements twice in a union.')
add('indices','Laws of indices','For the same non-zero base, multiplying powers adds exponents: a^m×a^n=a^(m+n).|Dividing powers subtracts exponents: a^m÷a^n=a^(m-n).|A power of a power multiplies exponents: (a^m)^n=a^(mn).|These rules do not generally simplify a sum such as a^m+a^n by adding exponents.','Expand powers into repeated factors, combine or cancel factors, then recover the rule.','Check that the bases match before using the product or quotient rule.')
add('exponential','Simple exponential equations','An exponential equation contains an unknown exponent.|When possible, write both sides with the same base.|If 2^x=32 and 32=2^5, then x=5.|Substitute the answer back into the original equation to verify it.','Create a table of powers of 2, 3 and 5 and use it to find missing exponents.','Do not find the exponent by dividing the right-hand value by the base.')
add('gradient','Gradient of a straight line','Gradient is vertical change divided by horizontal change.|For two points, m=(y2-y1)/(x2-x1), provided their x-values differ.|A line rising left to right has positive gradient; a falling line has negative gradient. A horizontal line has zero gradient.|In y=mx+c, m is gradient and c is the y-intercept. A vertical line has undefined gradient.','Plot points on squared paper and draw a rise/run triangle to count changes.','Use the same point order in both differences; do not reverse only one subtraction.')

WEEKS={4:[('place','words'),('chart','compare'),('round','skip'),('roman',),('factors','hcf'),('lcm','factors'),('facts',),('multiply','divide'),('divide','word'),('unit','equiv'),('simplify',),('fraccompare',)],5:[('place','words','chart'),('compare','round','skip'),('roman',),('factors',),('hcf','lcm'),('multiply',),('multiply','divide'),('word','integer'),('equiv','fraccompare'),('fracadd',),('fracmul',),('percent',)],6:[('place',),('words','chart'),('compare','round'),('facts',),('multiply',),('divide',),('mixed','fracadd'),('fracmul',),('ratio',),('ratioeq',),('proportion',),('rates','proportion')],7:[('place','words'),('round','decimalround'),('sigfig','ten'),('multiply','word'),('decimalops','multiply','divide'),('decimalops','powers'),('powers','primepower'),('powers','hcf'),('mixed','fraccompare'),('fracadd',),('fracmul',),('fracmul',)],8:[('words','skip'),('compare','standard'),('sigfig',),('place','sets'),('sets','ten'),('multiply','word'),('decimalops','multiply','divide'),('decimalops','indices'),('indices','exponential'),('powers','gradient'),('gradient',),('gradient',)]}
PAGES={4:20,5:22,6:19,7:40,8:48}
def fmt(x):
    if isinstance(x,F):return str(x.numerator) if x.denominator==1 else str(x)
    if isinstance(x,float):return f'{x:.6f}'.rstrip('0').rstrip('.')
    return str(x)
def roman(n):
    s=''
    for v,c in [(100,'C'),(90,'XC'),(50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]:
        while n>=v:s+=c;n-=v
    return s
def primefactors(n):
    fs=[];p=2
    while p*p<=n:
        while n%p==0:fs.append(p);n//=p
        p+=1
    if n>1:fs.append(n)
    return ' × '.join(map(str,fs))
def task(skill,g,r,v=0):
    v%=3;a=r.randint(2,9);b=r.randint(2,9);c=r.randint(2,8);wrong=None
    if skill=='place':
        cap={4:99999,5:999999,6:999999,7:8999999999,8:8999999999}[g];n=r.randint(cap//5,cap);p=r.randint(1,len(str(n))-2);digit=(n//10**p)%10
        if digit==0:n+=10**p;digit=1
        ans=digit*10**p;place={1:'tens',2:'hundreds',3:'thousands',4:'ten-thousands',5:'hundred-thousands',6:'millions',7:'ten-millions',8:'hundred-millions'}[p]
        q=f'What is the value of the digit in the {place} place in {n:,}?';method=f'The digit is {digit}; {digit} × {10**p:,} = {ans:,}.';wrong=[digit,digit*10**(p-1),digit*10**(p+1)]
        if v==1:ans=a*10000+b*100+c;q=f'A number has {a} ten-thousands, {b} hundreds and {c} ones, with zeros elsewhere. Write it in figures.';method=f'{a}×10,000 + {b}×100 + {c} = {ans:,}.';wrong=[a*1000+b*100+c,a*10000+b*1000+c,a*10000+b*100+10*c]
    elif skill=='words':
        from num2words import num2words
        cap={4:99999,5:999999,6:999999999,7:8999999999,8:8999999999}[g];n=r.randint(cap//5,cap);ans=n;q='Write in figures: '+num2words(n,lang='en')+'.';method=f'Place each named group in its correct scale: {n:,}.';wrong=[n+100,n+1000,n-1000]
    elif skill=='chart':
        n=r.randint(1100,8900)*10**max(0,g-4);width=r.choice([5,10]);step=r.choice([1,10,50]);direction=r.choice(['right','left','above','below']);change={'right':step,'left':-step,'above':-width*step,'below':width*step}[direction];ans=n+change;q=f'A {width}-column chart increases by {step} along each row. {n:,} is an interior entry. What number is immediately {direction} it?';method=f'Change = {change:+,}; {n:,} {change:+,} = {ans:,}.';wrong=[n-change,n,n+2*change]
    elif skill=='compare':
        n=r.randint(1100000000,8000000000) if g>=7 else r.randint(1000,9000)*10**(g-4);vals=r.sample(range(n,n+1000),4);ans=min(vals) if v==1 else max(vals);q=f'Which is the {"least" if v==1 else "greatest"} number: '+', '.join(f'{x:,}' for x in vals)+'?';wrong=[x for x in vals if x!=ans];method='Compare from the left. Ascending order: '+', '.join(f'{x:,}' for x in sorted(vals))+'.'
    elif skill=='round':
        cap=9999 if g==4 else 99999 if g<7 else 8999999999;n=r.randint(cap//10,cap);unit=r.choice([10,100,1000] if g<7 else [100,1000,10000,100000]);ans=(n+unit//2)//unit*unit;q=f'Round {n:,} to the nearest {unit:,}.';method=f'Neighbouring multiples: {n//unit*unit:,} and {(n//unit+1)*unit:,}. Nearest (halfway values rounded upward): {ans:,}.';wrong=[ans-unit,ans+unit,ans+2*unit]
    elif skill=='skip':
        step=r.choice([50,100] if g==4 else [500,1000] if g<7 else [10000,100000]);n=r.randint(10001,50000)*100000 if g==8 else r.randint(10,50)*step;step*=r.choice([-1,1]);ans=n+3*step;q=f'Find the next term: {n:,}, {n+step:,}, {n+2*step:,}, …';method=f'The constant step is {step:+,}; next term = {ans:,}.';wrong=[ans-step,ans+step,ans+2*step]
    elif skill=='roman':
        n=r.randint(2,30 if g==4 else 100)
        if v==1:ans=n;q=f'Write {roman(n)} in ordinary figures.';wrong=[n-1,n+1,n+2]
        else:ans=roman(n);q=f'Write {n} using standard Roman numerals.';wrong=[roman(n-1),roman(n+1),roman(n+2)]
        method=f'{n} = {roman(n)} using I=1, V=5, X=10, L=50, C=100 and permitted subtractive pairs.'
    elif skill=='factors':
        n=r.randint(10,50 if g==4 else 100);fs=[k for k in range(1,n+1) if n%k==0]
        if v==0:ans=len(fs);q=f'How many positive factors does {n} have?';method='Factors: '+', '.join(map(str,fs))+f'. Count = {ans}.'
        elif v==1:
            primes=[k for k in range(2,100) if all(k%d for d in range(2,isqrt(k)+1))];ans=r.choice(primes);wrong=r.sample([k for k in range(4,100) if k not in primes],3);q='Which number is prime: '+', '.join(map(str,sorted([ans]+wrong)))+'?';method=f'{ans} has exactly two positive factors: 1 and {ans}.'
        else:ans=r.choice(list(range(2,100,2)));wrong=r.sample(list(range(3,100,2)),3);q='Which number is even: '+', '.join(map(str,sorted([ans]+wrong)))+'?';method=f'{ans} is divisible by 2 with no remainder.'
    elif skill in ['hcf','lcm','primepower']:
        if g==4:a=r.randint(2,6);b=r.randint(2,6);c=r.randint(2,6)
        x=a*c;y=b*c;h=gcd(x,y)
        if skill=='lcm':ans=lcm(x,y);q=f'Find the LCM of {x} and {y}.';method=f'HCF={h}. LCM=({x}×{y})÷{h}={ans}.'
        else:
            ans=h;q=f'Find the HCF of {x} and {y}'+(' using prime factors.' if skill=='primepower' else '.');method='Common factors: '+', '.join(str(k) for k in range(1,min(x,y)+1) if x%k==y%k==0)+f'. Greatest = {h}.'
            if skill=='primepower':method=f'{x}={primefactors(x)}; {y}={primefactors(y)}. Multiply shared primes using the fewest copies of each: HCF={h}.'
    elif skill=='facts':
        x=r.randint(2,12 if g==4 else 9);y=r.randint(2,12 if g==4 else 9)
        if v==1:ans=y;q=f'Calculate {x*y} ÷ {x}.';method=f'{x}×{y}={x*y}, so {x*y}÷{x}={y}.'
        else:ans=x*y;q=f'Calculate {x} × {y}.';method=f'{x} equal groups of {y} contain {ans}. Check: {ans}÷{x}={y}.'
    elif skill=='multiply':
        x=r.randint(12,89) if g==4 else r.randint(101,499);y=r.randint(2,9) if g==4 else r.randint(12,299) if g==6 else r.randint(12,39);ans=x*y;t=y//10*10;u=y%10;q=f'Calculate {x} × {y}.';method=f'{x}×({t}+{u}) = {x*t}+{x*u} = {ans}.';wrong=[ans+x,ans-x,x+y]
    elif skill=='divide':
        divisor=r.randint(2,9);quot=r.randint(3,10) if g==4 else r.randint(12,99);n=divisor*quot;ans=quot;q=f'Calculate {n} ÷ {divisor}.';method=f'{divisor}×{quot}={n}, so the quotient is {quot}.';wrong=[quot+1,quot-1,n-divisor]
    elif skill=='word':
        packs=r.randint(3,9);each=r.randint(4,12);sold=r.randint(2,packs*each-1);ans=packs*each-sold;q=f'A shop has {packs} packs of {each} pencils and sells {sold} pencils. How many pencils remain?';method=f'Start with {packs}×{each}={packs*each}; subtract {sold} to obtain {ans} pencils.';wrong=[packs*each+sold,packs+each+sold,ans+each]
    elif skill=='integer':
        x=r.randint(-20,20);y=r.randint(2,15);op=r.choice(['+','−']);ans=x+y if op=='+' else x-y;q=f'Calculate ({x}) {op} {y}.';method=f'Start at {x} and move {y} places {"right" if op=="+" else "left"}: {ans}.'
    elif skill=='unit':
        den=r.randint(3,12)
        if v==0:ans=F(1,den);q=f'A strip is divided into {den} equal pieces. What fraction is one piece?';method=f'One of {den} equal parts is 1/{den}.'
        elif v==1:ans=den;q=f'How many jumps of 1/{den} go from 0 to 1 on a number line?';method=f'{den}×1/{den}=1.'
        else:ans=F(den-1,den);q=f'One of {den} equal slices is eaten. What fraction remains?';method=f'{den-1} of {den} equal slices remain: {ans}.'
    elif skill=='equiv':
        den=r.randint(3,12);num=r.randint(1,den-1);k=r.randint(2,6);ans=num*k;q=f'Complete: {num}/{den} = ?/{den*k}.';method=f'Multiply both terms by {k}; numerator = {num}×{k}={ans}.';wrong=[num+k,num,num*k+k]
    elif skill=='simplify':
        den=r.choice([3,5,7,11]);num=r.randint(1,den-1);k=r.randint(2,6)
        if v==1:
            whole=r.randint(1,4);n=whole*den+num;ans=f'{whole} {num}/{den}';q=f'Write {n}/{den} as a mixed number.';method=f'{n}÷{den}={whole} remainder {num}; mixed number = {ans}.';wrong=[f'{whole+1} {num}/{den}',f'{whole} {den-num}/{den}',f'{whole} {num}/{den+1}']
        else:ans=F(num,den);q=f'Write {num*k}/{den*k} in simplest form.';method=f'Divide both terms by {k}: {ans}.'
    elif skill=='fraccompare':
        pool=sorted(set(F(n,d) for d in [4,5,8,10,12] for n in range(1,d)));vals=r.sample(pool,4);ans=min(vals) if v==1 else max(vals);q=f'Which fraction is the {"least" if v==1 else "greatest"}: '+', '.join(map(fmt,vals))+'?';wrong=[x for x in vals if x!=ans];den=lcm(*(x.denominator for x in vals));method=f'Use denominator {den}: '+', '.join(f'{x}={x.numerator*(den//x.denominator)}/{den}' for x in vals)+f'. Answer: {ans}.'
    elif skill=='fracadd':
        x=F(r.randint(1,8),r.choice([2,3,4,6]));y=F(r.randint(1,8),r.choice([2,3,4,6]));op='−' if v==1 else '+'
        if op=='−' and x<y:x,y=y,x
        ans=x-y if op=='−' else x+y;den=lcm(x.denominator,y.denominator);nx=x.numerator*(den//x.denominator);ny=y.numerator*(den//y.denominator);q=f'Calculate {x} {op} {y}. Give the answer in simplest form.';method=f'Common denominator {den}: ({nx} {op} {ny})/{den} = {ans}.'
    elif skill=='fracmul':
        den=r.choice([3,4,5,8]);num=r.randint(1,den-1);x=F(num,den)
        if v!=2 or g<=5:total=den*r.randint(3,12);ans=x*total;q=f'Find {x} of {total}.';method=f'{total}÷{den}×{num}={ans}.'
        else:y=F(r.randint(1,4),r.randint(5,9));ans=x*y;q=f'Calculate {x} × {y}.';method=f'({x.numerator}×{y.numerator})/({x.denominator}×{y.denominator})={ans}.'
    elif skill=='percent':
        pc=r.choice([10,20,25,50,75]);n=r.choice([20,40,60,80]);reduction=F(pc*n,100);ans=reduction;q=f'Find {pc}% of {n}.';method=f'{pc}/100 × {n} = {ans}.'
        if v==1:ans=F(n)-reduction;q=f'A GH₵{n} item has a {pc}% discount. Find the new price in Ghana cedis.';method=f'Discount={reduction}; new price={n}-{reduction}={ans} Ghana cedis.'
    elif skill=='mixed':
        f=r.choice([F(1,2),F(1,4),F(3,4),F(1,5),F(2,5),F(3,5),F(4,5),F(1,10),F(3,10),F(7,10)])
        if v==0:ans=float(f);q=f'Write {f} as a decimal.';method=f'{f.numerator}÷{f.denominator}={fmt(ans)}.'
        elif v==1:ans=f*100;q=f'Write {f} as a percentage. Give the numerical percent value.';method=f'{f}×100={ans}%.'
        else:ans=f;q=f'Write {f*100}% as a fraction in simplest form.';method=f'{f*100}/100={f}.'
    elif skill=='ratio':
        x=a*c;y=b*c;h=gcd(x,y);ans=f'{x//h}:{y//h}';q=f'Simplify the ratio {x}:{y}.';method=f'Divide both terms by {h}: {ans}.';wrong=[f'{x//h+1}:{y//h}',f'{x//h}:{y//h+1}',f'{x//h+2}:{y//h}']
    elif skill=='ratioeq':ans=a*c;q=f'Complete: {a}:{b} = ?:{b*c}.';method=f'Multiply both terms by {c}; missing term={a}×{c}={ans}.'
    elif skill=='proportion':
        price=r.randint(2,15);n=r.randint(3,7);m=n+r.randint(2,7);ans=m*price;q=f'{n} notebooks cost GH₵{n*price}. At the same unit price, what do {m} notebooks cost in Ghana cedis?';method=f'Unit price={n*price}÷{n}={price}; cost={m}×{price}={ans}.'
    elif skill=='rates':scale=r.randint(2,9);cm=r.randint(3,12);ans=scale*cm;q=f'A map uses 1 cm for {scale} km. What distance in kilometres does {cm} cm represent?';method=f'{cm}×{scale}={ans} km.'
    elif skill=='decimalround':
        n=Decimal(r.randint(1001,99999))/1000;places=r.choice([1,2]);unit=Decimal(10)**-places;ans=format(n.quantize(unit,rounding=ROUND_HALF_UP),f'.{places}f');q=f'Round {n} to {places} decimal place(s).';method=f'Inspect the next digit and round directly: {ans}.';wrong=[format(Decimal(ans)+unit,f'.{places}f'),format(Decimal(ans)-unit,f'.{places}f'),format(Decimal(ans)+2*unit,f'.{places}f')]
    elif skill=='sigfig':n=r.randint(1011,9899);sf=r.choice([1,2,3]);power=10**(len(str(n))-sf);ans=(n+power//2)//power*power;q=f'Round {n:,} to {sf} significant figure(s).';method=f'Count {sf} places from the first non-zero digit, then round using the next digit: {ans:,}.';wrong=[ans-power,ans+power,ans+2*power]
    elif skill=='ten':n=F(r.randint(101,999),100);k=r.choice([10,100,1000]);divide=v==1;ans=float(n/k if divide else n*k);q=f'Calculate {fmt(float(n))} {"÷" if divide else "×"} {k}.';method=f'Change each digit’s place value by the factor {k}: {fmt(ans)}.'
    elif skill=='decimalops':
        x=F(r.randint(101,9999),100);y=F(r.randint(101,9999),100)
        if v==0:ans=x+y;q=f'Calculate {float(x):.2f} + {float(y):.2f}.';method=f'Add aligned hundredths: ({x*100}+{y*100})/100={float(ans):.2f}.'
        elif v==1:
            if x<y:x,y=y,x
            ans=x-y;q=f'Calculate {float(x):.2f} − {float(y):.2f}.';method=f'Subtract aligned hundredths: ({x*100}-{y*100})/100={float(ans):.2f}.'
        else:ans=x*a;q=f'{a} books cost GH₵{float(x):.2f} each. Find the total cost in Ghana cedis.';method=f'{a}×{float(x):.2f}={float(ans):.2f} Ghana cedis.'
        ans=float(ans)
    elif skill=='powers':base=r.randint(2,7);e=0 if v==1 else r.randint(2,4);ans=base**e;q=f'Evaluate {base}^{e}.';method=(f'A non-zero base to power zero equals 1.' if e==0 else ' × '.join([str(base)]*e)+f' = {ans}.')
    elif skill=='standard':coef=F(r.randint(11,99),10);power=r.randint(3,8);n=int(coef*10**power);ans=f'{float(coef):g} × 10^{power}';q=f'Write {n:,} in standard form.';method=f'{n:,}={ans}; the coefficient is at least 1 and less than 10.';wrong=[f'{float(coef):g} × 10^{power-1}',f'{float(coef):g} × 10^{power+1}',f'{float(coef)*10:g} × 10^{power}']
    elif skill=='sets':
        if v==2:ans=a;q=f'Find the non-negative square root of {a*a}.';method=f'{a}×{a}={a*a}, so the root is {a}.'
        else:
            start=r.randint(1,15);na=r.randint(3,7);nb=r.randint(3,7);overlap=r.randint(1,min(na,nb)-1);A=set(range(start,start+na));B=set(range(start+na-overlap,start+na-overlap+nb));result=A|B if v==0 else A&B;ans=len(result);q='A={'+', '.join(map(str,sorted(A)))+'}; B={'+', '.join(map(str,sorted(B)))+'}. How many elements are in their '+('union' if v==0 else 'intersection')+'?';method='Required set: {'+', '.join(map(str,sorted(result)))+f'}}. Count={ans}.'
    elif skill=='indices':
        base=r.randint(2,7);m=r.randint(3,7);n=r.randint(1,3)
        if v==0:ans=m+n;q=f'Write {base}^{m} × {base}^{n} as {base}^k. Find k.';method=f'Add exponents: {m}+{n}={ans}.'
        elif v==1:ans=m-n;q=f'Write {base}^{m} ÷ {base}^{n} as {base}^k. Find k.';method=f'Subtract exponents: {m}-{n}={ans}.'
        else:ans=m*n;q=f'Write ({base}^{m})^{n} as {base}^k. Find k.';method=f'Multiply exponents: {m}×{n}={ans}.'
    elif skill=='exponential':base=r.randint(2,5);ans=r.randint(2,6);q=f'Solve {base}^x={base**ans} for x.';method=f'{base**ans}={base}^{ans}, so x={ans}.'
    elif skill=='gradient':
        m=r.choice([-3,-2,-1,1,2,3,4]);x1=r.randint(-3,3);x2=x1+r.randint(2,6);intercept=r.randint(-5,5);y1=m*x1+intercept;y2=m*x2+intercept
        if v==0:ans=m;q=f'Find the gradient through ({x1}, {y1}) and ({x2}, {y2}).';method=f'({y2}-({y1}))/({x2}-({x1}))={y2-y1}/{x2-x1}={m}.'
        elif v==1:ans=y2;q=f'A line is y={m}x{intercept:+}. Find y when x={x2}.';method=f'Substitute: y={m}×({x2}){intercept:+}={ans}.'
        else:ans=intercept;q=f'A line has gradient {m} and passes through ({x1}, {y1}). Find c in y={m}x+c.';method=f'c=y-mx={y1}-({m}×({x1}))={intercept}.'
    else:raise ValueError(skill)
    if wrong is None:wrong=[ans+1,ans-1,ans+2]
    answer=fmt(ans);alternatives=[]
    for x in wrong:
        s=fmt(x)
        if s!=answer and s not in alternatives:alternatives.append(s)
    i=3
    while len(alternatives)<3:
        if not isinstance(ans,(int,float,F)):raise ValueError(('Duplicate text distractor',skill,ans,wrong))
        s=fmt(ans+i);i+=1
        if s!=answer and s not in alternatives:alternatives.append(s)
    return {'q':q,'answer':answer,'wrong':alternatives[:3],'method':method,'skill':skill}
