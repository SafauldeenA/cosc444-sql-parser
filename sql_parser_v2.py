from collections import defaultdict
import re

keyword_list = [
    ',', '.', ';', 'SELECT', 'DISTINCT', 'FROM', 'WHERE', 'GROUP', 'BY', 'HAVING', 'ORDER', 'DELETE', 'UPDATE', 'SET', 'INSERT', 'INTO', 'VALUES',
    'ASC', 'DESC', 'RIGHT', 'LEFT', 'INNER', 'FULL', 'JOIN', 'ON', 'AS', 
    'SUM', 'AVG', 'COUNT', 'MAX', 'MIN', 'UPPER', 'LOWER', 'ROUND', 'LENGTH', 'ABS', 'AND', 'OR', 'LIKE', 'IS', 'NOT', 'NULL', 
    'users', 'orders', 'id', 'email', 'first_name', 'last_name', 'user_id', 'date', 'amount',
    '<=', '>=', '!=', '+', '-', '*', '/', '=', '<', '>', '(', ')'
]

keywords = defaultdict(set)
for k in keyword_list:
    keywords[len(k)].add(k)

class Parser:
    def __init__(self, input):
        self.string_input = input
        self.input = []
        self.input_index_map = []
        self.index = 0

    def tokenize(self, input):
        tokenized_input = []
        index_map = []
        i = 0
        while i < len(input):
            i = self.skip_whitespace(input, i)
            token = None
            substring = input[i:]

            # string
            match = re.search(r"^'(.*?)'", substring)
            if not token and match:
                token = substring[match.start():match.end()]

            # float - its important to do this before int
            match = re.search(r"^\d+\.\d+", substring)
            if not token and match:
                token = substring[match.start():match.end()]

            # integer
            match = re.search(r"^\d+", substring)
            if not token and match:
                token = substring[match.start():match.end()]

            # multi-line comments
            match = re.search(r"^/\*.*?\*/", substring, re.DOTALL)
            if not token and match:
                token = substring[match.start():match.end()]

            if not token:    
                for l in sorted(keywords.keys(), reverse=True):
                    if substring[:l] in keywords[l]:
                        token = substring[:l]
                        break
            
            if token is not None:
                tokenized_input.append(token)
                index_map.append((i, i + len(token)))
                i += len(token)
            elif substring.strip() == '': # check for empty string
                break
            else:
                raise SyntaxError(f'Tokenization Error at {i}. Expected: {["<string>", "<float>", "<integer>", "<comment>", "<token>"]}')
        
        return tokenized_input, index_map
    
    def skip_whitespace(self, input, i):
        pattern = r'\S'
        match = re.search(pattern, input[i:])
        if match:
            return i + match.end() - 1
        else:
            return i
        
    def consume(self, token):
        try:
            if self.peek() == token:
                self.index += 1
            else:
                self.raise_exception(token)
        except IndexError as e:
            raise self.raise_exception(token, len(self.input - 1), 'None') # TODO: fix the length calculation here

    def peek(self):
        if self.index < len(self.input):
            return self.input[self.index]
        else:
            return None
    
    def look_ahead(self):
        if self.index + 1 < len(self.input):
            return self.input[self.index + 1]
        else: 
            return None

    def look_ahead_n(self, n):
        if self.index + n < len(self.input):
            return self.input[self.index + n]
        else: 
            return None


    def untokenize_index(self, i):
        # this turns a n index for the token array into an index for the original string
        return self.input_index_map[i]

    def raise_exception(self, expected, i = None, got = None):
        # i = token index
        if i is None:
            i = min(self.index, len(self.input) - 1)
        i = self.untokenize_index(i)
        error_stmt = f'Syntax Error at {i}. Expected {expected}, but Got {got if got else self.peek()}'
        raise SyntaxError(error_stmt)

    def parse(self):
        try:
            self.input, self.input_index_map = self.tokenize(self.string_input)
            self.parse_sql()
            if self.index == len(self.input):
                return 'Parsed'
            else:
                self.raise_exception('<longer input>')
        except SyntaxError as e:
            return e.msg

    # databas tables & fields
    def parse_table(self):
        tables = ['users', 'orders']
        if self.peek() in tables:    
            self.consume(self.peek())
        else:
            self.raise_exception(tables)

    def parse_field(self):
        fields = ['id', 'email', 'first_name', 'last_name', 'user_id', 'date', 'amount']
        if self.peek() in fields:    
            self.consume(self.peek())
        else:
            self.raise_exception(fields)
        
    def parse_table_field(self):
        fields = ['id', 'email', 'first_name', 'last_name', 'user_id', 'date', 'amount']
        if self.peek() in fields:
            self.parse_field()
        else:
            self.parse_table()
            self.consume('.')
            self.parse_field()
        
    # basic definitions
    def parse_string(self):
        match = re.search(r"^'[^']*'$", self.peek())
        if match:
            self.consume(self.peek())
        else:
            self.raise_exception('<string>')
        
    def parse_float(self):
        match = re.search(r"^\d+\.\d+$", self.peek())
        if match:
            self.consume(self.peek())
        else:
            self.raise_exception('<float>')

    def parse_integer(self):
        match = re.search(r"^\d+$", self.peek())
        if match:
            self.consume(self.peek())
        else:
            self.raise_exception('<float>')

    def parse_value(self):
        if self.peek() is not None and re.search(r"^'[^']*'$", self.peek()):
            self.parse_string()
        elif self.peek() is not None and re.search(r"^\d+\.\d+$", self.peek()): # important that float be done first since it overlaps with integer definition
            self.parse_float()
        elif self.peek() is not None and  re.search(r"^\d+$", self.peek()):
            self.parse_integer()
        else:
            self.raise_exception(['<string>', '<float>', '<integer>'])

    def parse_alias(self):
        self.parse_string()

    def parse_function(self):
        functions = ['UPPER', 'LOWER', 'ROUND', 'LENGTH', 'ABS', 'SUM', 'AVG', 'COUNT', 'MAX', 'MIN']
        if self.peek() in functions:
             self.consume(self.peek())
        else:
            self.raise_exception(functions)
    
    def parse_math_operator(self):
        math_operators = ['+', '-', '*', '/']
        if self.peek() in math_operators:
             self.consume(self.peek())
        else:
            self.raise_exception(math_operators)
        
    def parse_comparison_operator(self):
        comparison_operators = ['<=', '>=', '!=', '=', '<', '>']
        if self.peek() in comparison_operators:
             self.consume(self.peek())
        else:
            self.raise_exception(comparison_operators)

    def parse_term(self):
        if self.peek() == '(':
            self.consume('(')
            self.parse_math_expression()
            self.consume(')')
        elif self.peek() is not None and (re.search(r"^'[^']*'$", self.peek()) or re.search(r"^\d+\.\d+$", self.peek()) or re.search(r"^\d+$", self.peek())):
            self.parse_value()
        else:
            self.parse_table_field()
        
    def parse_math_expression(self):
        functions = ['UPPER', 'LOWER', 'ROUND', 'LENGTH', 'ABS', 'SUM', 'AVG', 'COUNT', 'MAX', 'MIN']
        math_operators = ['+', '-', '*', '/']
        if self.peek() in functions:
            self.parse_function()
            self.consume('(')
            self.parse_math_expression()
            self.consume(')')
        else:
            self.parse_term()
            if self.peek() in math_operators: # optional part
                self.parse_optional_math_clause()

    def parse_optional_math_clause(self):
        math_operators = ['+', '-', '*', '/']
        self.parse_math_operator() 
        self.parse_term()
        if self.peek() in math_operators: # optional part
            self.parse_optional_math_clause()

    def parse_boolean_expression(self):
        tables = ['users', 'orders']
        fields = ['id', 'email', 'first_name', 'last_name', 'user_id', 'date', 'amount']
        if (self.peek() in fields and self.look_ahead() in ['LIKE', 'IS']) or \
           (self.peek() in tables and self.look_ahead() == '.' and self.look_ahead_n(2) in fields and self.look_ahead_n(3) in ['LIKE', 'IS']): # look-ahead for <table-field> followed by LIKE or IS
            self.parse_table_field()
            if self.peek() == 'LIKE':
                self.consume('LIKE')
                self.parse_string()
            elif self.peek() == 'IS':
                self.consume('IS')
                if self.peek() == 'NOT': # optional
                    self.consume('NOT')
                self.consume('NULL')
            else:
                self.raise_exception(['LIKE <string>', 'IS [NOT] NULL'])
        else:
            self.parse_math_expression()
            self.parse_comparison_operator()
            self.parse_math_expression()
    
    def parse_condition(self):
        self.parse_boolean_expression()
        if self.peek() in ['AND', 'OR']:
            self.consume(self.peek())
            self.parse_condition()

    # lists
    def parse_value_list(self):
        self.parse_value()
        if self.peek() in [',']:
            self.consume(self.peek())
            self.parse_value_list()
        
    def parse_field_list(self):
        self.parse_table_field()
        if self.peek() in [',']:
            self.consume(self.peek())
            self.parse_field_list()

    def parse_assignment_list(self):

        #  <table-field> = <value>
        self.parse_table_field()
        if self.peek() in ['=']:
            self.consume(self.peek())
        else:
            self.raise_exception('=')
        self.parse_value()

        #  [, <assignment-list>]
        if self.peek() in [',']:
            self.consume(self.peek())
            self.parse_assignment_list()

    

    # query helpers (mostly for select queries)
    
    def parse_field_alias_list(self):
        #  <field-alias>
        self.parse_field_alias()
        #  [, <field-alias-list>]
        if self.peek() in [',']:
            self.consume(self.peek())
            self.parse_field_alias_list()

    def parse_table_alias_list(self):
        #  <table-alias>
        self.parse_table_alias()
        #  [, <table-alias-list>]
        if self.peek() in [',']:
            self.consume(self.peek())
            self.parse_table_alias_list()


    def parse_order_list(self):
        # <order-item>
        self.parse_order_item()
        #  [, <order_list>]
        if self.peek() in [',']:
            self.consume(self.peek())
            self.parse_order_list()

    def parse_order_item(self):
        # <table-field>
        self.parse_table_field()
        # [ASC | DESC]
        if self.peek() in ['ASC', 'DESC']:
            self.consume(self.peek())



    def parse_select_clause(self):
        if self.peek() == '*':
            self.consume('*')
        else:
            self.parse_field_alias_list()

    def parse_field_alias_list(self):
        
        self.parse_field_alias()
        if self.peek() == ',':
            self.consume(',')
            self.parse_field_alias_list()

    def parse_field_alias(self):
        functions = ['UPPER', 'LOWER', 'ROUND', 'LENGTH', 'ABS', 'SUM', 'AVG', 'COUNT', 'MAX', 'MIN']
        if self.peek() in functions:
            self.parse_function()
            self.consume('(')
            self.parse_table_field()
            self.consume(')')
            if self.peek() == 'AS':
                self.consume('AS')
                self.parse_alias()
        else:
            self.parse_table_field()
            if self.peek() == 'AS':
                self.consume('AS')
                self.parse_alias()

    def parse_table_alias(self):
        self.parse_table()
        if self.peek() == 'AS':
            self.consume('AS')
            self.parse_alias()

    def parse_table_clause(self):
        self.parse_table()
        self.parse_optional_join_clause()

    def parse_optional_join_clause(self):
        if self.peek() == 'RIGHT' or self.peek() == 'LEFT' or self.peek() == 'INNER' or self.peek() == 'FULL':
            self.parse_join_clause()
            self.parse_optional_join_clause()

    def parse_join_clause(self):
        self.parse_join_type()
        self.consume('JOIN')
        self.parse_table()
        self.consume('ON')
        self.parse_condition()

    def parse_join_type(self):
        join_types = ['RIGHT', 'LEFT', 'INNER', 'FULL']
        if self.peek() in join_types:
            self.consume(self.peek())
        else:
            self.raise_exception(join_types)     
        

    # basic queries
    def parse_insert_query(self):
        self.consume('INSERT')
        self.consume('INTO')
        self.parse_table()
        self.consume('(')
        self.parse_field_list()
        self.consume(')')
        self.consume('VALUES')
        self.consume('(')
        self.parse_value_list()
        self.consume(')')

    def parse_update_query(self):
        self.consume('UPDATE')
        self.parse_table()
        self.consume('SET')
        self.consume('(')
        self.parse_assignment_list()
        self.consume(')')
        if self.peek() == 'WHERE':
            self.consume('WHERE')
            self.parse_condition()

    def parse_delete_query(self):
        self.consume('DELETE')
        self.consume('FROM')
        self.parse_table()
        if self.peek() == 'WHERE':
            self.consume('WHERE')
            self.parse_condition()

    # select query
    def parse_select_query(self):
        self.consume('SELECT')
        if self.peek() == 'DISTINCT':
            self.consume('DISTINCT')
        self.parse_select_clause()
        self.consume('FROM')
        self.parse_table_clause()
        if self.peek() == 'WHERE':
            self.consume('WHERE')
            self.parse_condition()
        if self.peek() == 'GROUP':
            self.consume('GROUP')
            self.consume('BY')
            self.parse_field_list()
        if self.peek() == 'HAVING':
            self.consume('HAVING')
            self.parse_condition()
        if self.peek() == 'ORDER':
            self.consume('ORDER')
            self.consume('BY')
            self.parse_order_list()

    # big picture sql
    def parse_comment(self):
        match = re.search(r'^\s*/\*.*?\*/\s*$', self.peek(), re.DOTALL)
        if match:
            self.consume(self.peek())
        else:
            self.raise_exception('<commment>')

    def parse_statement(self):
        if self.peek() == 'SELECT':
            self.parse_select_query()
            self.consume(';')
        elif self.peek() == 'INSERT':
            self.parse_insert_query()
            self.consume(';')
        elif self.peek() == 'UPDATE':
            self.parse_update_query()
            self.consume(';')
        elif self.peek() == 'DELETE':
            self.parse_delete_query()
            self.consume(';')
        elif self.peek().startswith('/*'):
            self.parse_comment()
        else:
            self.raise_exception(['<select>', '<insert>', '<update>', '<delete>', '<comment>'])

    def parse_sql(self):
        self.parse_statement()
        if self.peek() is not None:
            self.parse_sql()



test_cases = [
"""

SELECT DISTINCT users.first_name AS 'Given Name', users.last_name AS 'Surname', SUM(users.id) AS 'Total Spent on Large Orders'
FROM users
RIGHT JOIN orders ON users.id = orders.user_id
WHERE users.id IS NOT NULL AND users.email LIKE '%@hotmail.com' AND orders.amount >= ((100) * 1.05) - (5)
GROUP BY users.id
HAVING SUM(orders.amount) > 1000 AND COUNT(orders.id) > 5
ORDER BY users.first_name DESC, users.last_name DESC;
""",
]

for test in test_cases:
    parser = Parser(test)
    print(parser.parse())
