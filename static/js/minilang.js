class MiniLangError extends Error {
    constructor(message, phase, line, column) {
        super(message);
        this.phase = phase;
        this.line = line;
        this.column = column;
        this.name = "MiniLangError";
    }
}
class Lexer {
    constructor(source) {
        this.source = source;
        this.offset = 0;
        this.line = 1;
        this.column = 1;
        this.tokens = [];
        this.keywords = {
            let: "let", if: "if", else: "else", while: "while", print: "print", true: "true", false: "false",
        };
    }
    scan() {
        while (!this.atEnd()) {
            const char = this.peek();
            if (/\s/.test(char)) {
                this.advance();
                continue;
            }
            if (char === "/" && this.peekNext() === "/") {
                this.skipComment();
                continue;
            }
            if (/[A-Za-z_]/.test(char)) {
                this.identifier();
                continue;
            }
            if (/[0-9]/.test(char)) {
                this.number();
                continue;
            }
            if (char === '"') {
                this.string();
                continue;
            }
            if (this.operator())
                continue;
            if ("(){};,".includes(char)) {
                this.add("punctuation", this.advance());
                continue;
            }
            throw this.error(`Unexpected character ${JSON.stringify(char)}.`);
        }
        this.tokens.push({ kind: "eof", lexeme: "", line: this.line, column: this.column });
        return this.tokens;
    }
    identifier() {
        const start = this.offset;
        const line = this.line;
        const column = this.column;
        while (/[A-Za-z0-9_]/.test(this.peek()) && !this.atEnd())
            this.advance();
        const lexeme = this.source.slice(start, this.offset);
        const kind = this.keywords[lexeme];
        if (kind === "true" || kind === "false") {
            this.tokens.push({ kind, lexeme, value: kind === "true", line, column });
        }
        else {
            this.tokens.push({ kind: kind ?? "identifier", lexeme, line, column });
        }
    }
    number() {
        const start = this.offset;
        const line = this.line;
        const column = this.column;
        while (/[0-9]/.test(this.peek()) && !this.atEnd())
            this.advance();
        if (this.peek() === "." && /[0-9]/.test(this.peekNext())) {
            this.advance();
            while (/[0-9]/.test(this.peek()) && !this.atEnd())
                this.advance();
        }
        const lexeme = this.source.slice(start, this.offset);
        this.tokens.push({ kind: "number", lexeme, value: Number(lexeme), line, column });
    }
    string() {
        const line = this.line;
        const column = this.column;
        const start = this.offset;
        this.advance();
        let value = "";
        while (!this.atEnd() && this.peek() !== '"') {
            if (this.peek() === "\n" || this.peek() === "\r")
                throw this.error("String literals cannot span lines.");
            if (this.peek() === "\\") {
                this.advance();
                const escaped = this.peek();
                const escapes = { n: "\n", t: "\t", '"': '"', "\\": "\\" };
                if (!(escaped in escapes))
                    throw this.error(`Unsupported escape sequence \\${escaped}.`);
                value += escapes[escaped];
                this.advance();
            }
            else {
                value += this.advance();
            }
        }
        if (this.atEnd())
            throw new MiniLangError("Unterminated string literal.", "Lexical", line, column);
        this.advance();
        this.tokens.push({ kind: "string", lexeme: this.source.slice(start, this.offset), value, line, column });
    }
    operator() {
        const line = this.line;
        const column = this.column;
        const pair = this.peek() + this.peekNext();
        if (["==", "!=", ">=", "<=", "&&", "||"].includes(pair)) {
            this.advance();
            this.advance();
            this.tokens.push({ kind: "operator", lexeme: pair, line, column });
            return true;
        }
        if ("+-*/%><=!=".includes(this.peek())) {
            const lexeme = this.advance();
            this.tokens.push({ kind: "operator", lexeme, line, column });
            return true;
        }
        if (this.peek() === "=") {
            this.add("operator", this.advance());
            return true;
        }
        return false;
    }
    skipComment() { while (!this.atEnd() && this.peek() !== "\n")
        this.advance(); }
    add(kind, lexeme) { this.tokens.push({ kind, lexeme, line: this.line, column: this.column - lexeme.length }); }
    peek() { return this.source[this.offset] ?? "\0"; }
    peekNext() { return this.source[this.offset + 1] ?? "\0"; }
    atEnd() { return this.offset >= this.source.length; }
    advance() {
        const char = this.source[this.offset++] ?? "\0";
        if (char === "\n") {
            this.line++;
            this.column = 1;
        }
        else {
            this.column++;
        }
        return char;
    }
    error(message) { return new MiniLangError(message, "Lexical", this.line, this.column); }
}
class Parser {
    constructor(tokens) {
        this.tokens = tokens;
        this.current = 0;
    }
    parse() {
        const statements = [];
        while (!this.check("eof"))
            statements.push(this.statement());
        return statements;
    }
    statement() {
        if (this.match("let"))
            return this.declaration(this.previous());
        if (this.match("if"))
            return this.ifStatement(this.previous());
        if (this.match("while"))
            return this.whileStatement(this.previous());
        if (this.match("print"))
            return this.printStatement(this.previous());
        if (this.check("identifier") && this.peekNext().lexeme === "=")
            return this.assignment();
        if (this.matchLexeme("{"))
            return this.block(this.previous());
        throw this.error(this.peek(), "Expected a declaration, assignment, print, if, while, or block.");
    }
    declaration(start) {
        const name = this.consume("identifier", "Expected a variable name after 'let'.");
        this.consumeLexeme("=", "Expected '=' after the variable name.");
        const initializer = this.expression();
        this.consumeLexeme(";", "Expected ';' after the declaration.");
        return { kind: "declaration", name: name.lexeme, initializer, line: start.line, column: start.column };
    }
    assignment() {
        const name = this.consume("identifier", "Expected a variable name.");
        this.consumeLexeme("=", "Expected '=' after the variable name.");
        const value = this.expression();
        this.consumeLexeme(";", "Expected ';' after the assignment.");
        return { kind: "assignment", name: name.lexeme, value, line: name.line, column: name.column };
    }
    printStatement(start) {
        this.consumeLexeme("(", "Expected '(' after 'print'.");
        const expression = this.expression();
        this.consumeLexeme(")", "Expected ')' after the printed expression.");
        this.consumeLexeme(";", "Expected ';' after the print statement.");
        return { kind: "print", expression, line: start.line, column: start.column };
    }
    ifStatement(start) {
        this.consumeLexeme("(", "Expected '(' after 'if'.");
        const condition = this.expression();
        this.consumeLexeme(")", "Expected ')' after the condition.");
        const thenBranch = this.block(this.consumeLexeme("{", "Expected a block after the condition."));
        let elseBranch = null;
        if (this.match("else"))
            elseBranch = this.block(this.consumeLexeme("{", "Expected a block after 'else'.")).statements;
        return { kind: "if", condition, thenBranch: thenBranch.statements, elseBranch, line: start.line, column: start.column };
    }
    whileStatement(start) {
        this.consumeLexeme("(", "Expected '(' after 'while'.");
        const condition = this.expression();
        this.consumeLexeme(")", "Expected ')' after the condition.");
        const body = this.block(this.consumeLexeme("{", "Expected a block after the condition."));
        return { kind: "while", condition, body: body.statements, line: start.line, column: start.column };
    }
    block(start) {
        const statements = [];
        while (!this.check("eof") && !this.checkLexeme("}"))
            statements.push(this.statement());
        this.consumeLexeme("}", "Expected '}' after the block.");
        return { kind: "block", statements, line: start.line, column: start.column };
    }
    expression() { return this.logicalOr(); }
    logicalOr() { return this.binaryChain(() => this.logicalAnd(), ["||"]); }
    logicalAnd() { return this.binaryChain(() => this.equality(), ["&&"]); }
    equality() { return this.binaryChain(() => this.comparison(), ["==", "!="]); }
    comparison() { return this.binaryChain(() => this.term(), [">", ">=", "<", "<="]); }
    term() { return this.binaryChain(() => this.factor(), ["+", "-"]); }
    factor() { return this.binaryChain(() => this.unary(), ["*", "/", "%"]); }
    binaryChain(next, operators) {
        let expression = next();
        while (operators.includes(this.peek().lexeme)) {
            const operator = this.advance();
            const right = next();
            expression = { kind: "binary", operator: operator.lexeme, left: expression, right, line: operator.line, column: operator.column };
        }
        return expression;
    }
    unary() {
        if (["!", "-", "+"].includes(this.peek().lexeme)) {
            const operator = this.advance();
            return { kind: "unary", operator: operator.lexeme, operand: this.unary(), line: operator.line, column: operator.column };
        }
        return this.primary();
    }
    primary() {
        const token = this.peek();
        if (this.match("number")) {
            const value = Number(token.value);
            return { kind: "literal", value, valueType: token.lexeme.includes(".") ? "float" : "integer", line: token.line, column: token.column };
        }
        if (this.match("string"))
            return { kind: "literal", value: String(token.value), valueType: "string", line: token.line, column: token.column };
        if (this.match("true") || this.match("false"))
            return { kind: "literal", value: token.kind === "true", valueType: "boolean", line: token.line, column: token.column };
        if (this.match("identifier"))
            return { kind: "variable", name: token.lexeme, line: token.line, column: token.column };
        if (this.matchLexeme("(")) {
            const expression = this.expression();
            this.consumeLexeme(")", "Expected ')' after the expression.");
            return expression;
        }
        throw this.error(token, "Expected a literal, variable, or parenthesized expression.");
    }
    match(kind) { if (!this.check(kind))
        return false; this.advance(); return true; }
    matchLexeme(lexeme) { if (!this.checkLexeme(lexeme))
        return false; this.advance(); return true; }
    check(kind) { return this.peek().kind === kind; }
    checkLexeme(lexeme) { return this.peek().lexeme === lexeme; }
    consume(kind, message) { if (this.check(kind))
        return this.advance(); throw this.error(this.peek(), message); }
    consumeLexeme(lexeme, message) { if (this.checkLexeme(lexeme))
        return this.advance(); throw this.error(this.peek(), message); }
    advance() { if (!this.check("eof"))
        this.current++; return this.previous(); }
    peek() { return this.tokens[this.current] ?? this.tokens[this.tokens.length - 1]; }
    peekNext() { return this.tokens[this.current + 1] ?? this.tokens[this.tokens.length - 1]; }
    previous() { return this.tokens[this.current - 1]; }
    error(token, message) { return new MiniLangError(message, "Syntax", token.line, token.column); }
}
class SemanticAnalyzer {
    constructor() {
        this.scopes = [new Map()];
    }
    analyze(statements) { for (const statement of statements)
        this.visit(statement); }
    visit(statement) {
        switch (statement.kind) {
            case "declaration": {
                const type = this.typeOf(statement.initializer);
                if (this.scopes[this.scopes.length - 1].has(statement.name))
                    this.fail(statement, `Variable '${statement.name}' is already declared in this block.`);
                this.scopes[this.scopes.length - 1].set(statement.name, type);
                return;
            }
            case "assignment": {
                const existing = this.lookup(statement.name);
                if (!existing)
                    this.fail(statement, `Variable '${statement.name}' is not declared.`);
                const actual = this.typeOf(statement.value);
                if (!this.assignable(existing, actual))
                    this.fail(statement, `Cannot assign ${actual} to ${existing} variable '${statement.name}'.`);
                return;
            }
            case "print":
                this.typeOf(statement.expression);
                return;
            case "block":
                this.withScope(statement.statements);
                return;
            case "if":
                this.requireBoolean(statement.condition, "if");
                this.withScope(statement.thenBranch);
                if (statement.elseBranch)
                    this.withScope(statement.elseBranch);
                return;
            case "while":
                this.requireBoolean(statement.condition, "while");
                this.withScope(statement.body);
        }
    }
    typeOf(expression) {
        if (expression.kind === "literal")
            return expression.valueType;
        if (expression.kind === "variable") {
            const type = this.lookup(expression.name);
            if (!type)
                this.fail(expression, `Variable '${expression.name}' is not declared.`);
            return type;
        }
        if (expression.kind === "unary") {
            const operand = this.typeOf(expression.operand);
            if (expression.operator === "!") {
                if (operand !== "boolean")
                    this.fail(expression, "Operator '!' requires a boolean operand.");
                return "boolean";
            }
            if (!this.isNumeric(operand))
                this.fail(expression, `Unary '${expression.operator}' requires a numeric operand.`);
            return operand;
        }
        const left = this.typeOf(expression.left);
        const right = this.typeOf(expression.right);
        const op = expression.operator;
        if (op === "&&" || op === "||") {
            if (left !== "boolean" || right !== "boolean")
                this.fail(expression, `Operator '${op}' requires boolean operands.`);
            return "boolean";
        }
        if (op === "==" || op === "!=") {
            if (!this.assignable(left, right))
                this.fail(expression, `Cannot compare ${left} with ${right}.`);
            return "boolean";
        }
        if ([">", ">=", "<", "<="].includes(op)) {
            const numbers = this.isNumeric(left) && this.isNumeric(right);
            if (!numbers && !(left === "string" && right === "string"))
                this.fail(expression, `Operator '${op}' requires matching numbers or strings.`);
            return "boolean";
        }
        if (op === "+" && left === "string" && right === "string")
            return "string";
        if (!this.isNumeric(left) || !this.isNumeric(right))
            this.fail(expression, `Operator '${op}' requires numeric operands.`);
        if (op === "%" && (left !== "integer" || right !== "integer"))
            this.fail(expression, "Operator '%' requires integer operands.");
        return op === "/" || left === "float" || right === "float" ? "float" : "integer";
    }
    requireBoolean(expression, construct) {
        if (this.typeOf(expression) !== "boolean")
            this.fail(expression, `The ${construct} condition must be boolean.`);
    }
    withScope(statements) {
        this.scopes.push(new Map());
        for (const statement of statements)
            this.visit(statement);
        this.scopes.pop();
    }
    lookup(name) {
        for (let index = this.scopes.length - 1; index >= 0; index--) {
            const type = this.scopes[index].get(name);
            if (type)
                return type;
        }
        return undefined;
    }
    assignable(target, value) { return target === value || (target === "float" && value === "integer"); }
    isNumeric(type) { return type === "integer" || type === "float"; }
    fail(node, message) { throw new MiniLangError(message, "Semantic", node.line, node.column); }
}
function optimizeExpression(expression, stats) {
    if (expression.kind === "literal" || expression.kind === "variable")
        return expression;
    if (expression.kind === "unary") {
        const operand = optimizeExpression(expression.operand, stats);
        if (operand.kind === "literal") {
            const value = expression.operator === "!" ? !operand.value : expression.operator === "-" ? -Number(operand.value) : Number(operand.value);
            stats.folded++;
            return { kind: "literal", value, valueType: expression.operator === "!" ? "boolean" : operand.valueType, line: expression.line, column: expression.column };
        }
        return { ...expression, operand };
    }
    const left = optimizeExpression(expression.left, stats);
    const right = optimizeExpression(expression.right, stats);
    if (left.kind !== "literal" || right.kind !== "literal")
        return { ...expression, left, right };
    const a = left.value;
    const b = right.value;
    const op = expression.operator;
    let value;
    if (op === "/" && Number(b) === 0)
        return { ...expression, left, right };
    switch (op) {
        case "+":
            value = typeof a === "string" ? a + String(b) : Number(a) + Number(b);
            break;
        case "-":
            value = Number(a) - Number(b);
            break;
        case "*":
            value = Number(a) * Number(b);
            break;
        case "/":
            value = Number(a) / Number(b);
            break;
        case "%":
            if (Number(b) === 0)
                return { ...expression, left, right };
            value = Number(a) % Number(b);
            break;
        case "==":
            value = a === b;
            break;
        case "!=":
            value = a !== b;
            break;
        case ">":
            value = a > b;
            break;
        case ">=":
            value = a >= b;
            break;
        case "<":
            value = a < b;
            break;
        case "<=":
            value = a <= b;
            break;
        case "&&":
            value = Boolean(a) && Boolean(b);
            break;
        case "||":
            value = Boolean(a) || Boolean(b);
            break;
        default: return { ...expression, left, right };
    }
    stats.folded++;
    const valueType = typeof value === "boolean" ? "boolean" : typeof value === "string" ? "string" : Number.isInteger(value) ? "integer" : "float";
    return { kind: "literal", value, valueType, line: expression.line, column: expression.column };
}
function optimizeStatements(statements, stats) {
    const optimized = [];
    for (const statement of statements) {
        if (statement.kind === "declaration")
            optimized.push({ ...statement, initializer: optimizeExpression(statement.initializer, stats) });
        else if (statement.kind === "assignment")
            optimized.push({ ...statement, value: optimizeExpression(statement.value, stats) });
        else if (statement.kind === "print")
            optimized.push({ ...statement, expression: optimizeExpression(statement.expression, stats) });
        else if (statement.kind === "block")
            optimized.push({ ...statement, statements: optimizeStatements(statement.statements, stats) });
        else if (statement.kind === "if") {
            const condition = optimizeExpression(statement.condition, stats);
            const thenBranch = optimizeStatements(statement.thenBranch, stats);
            const elseBranch = statement.elseBranch ? optimizeStatements(statement.elseBranch, stats) : null;
            if (condition.kind === "literal" && typeof condition.value === "boolean") {
                stats.unreachable++;
                optimized.push({ kind: "block", statements: condition.value ? thenBranch : (elseBranch ?? []), line: statement.line, column: statement.column });
            }
            else
                optimized.push({ ...statement, condition, thenBranch, elseBranch });
        }
        else {
            const condition = optimizeExpression(statement.condition, stats);
            if (condition.kind === "literal" && condition.value === false) {
                stats.unreachable++;
                continue;
            }
            optimized.push({ ...statement, condition, body: optimizeStatements(statement.body, stats) });
        }
    }
    return optimized;
}
class TacGenerator {
    constructor() {
        this.temporary = 0;
        this.label = 0;
        this.lines = [];
    }
    generate(statements) { for (const statement of statements)
        this.statement(statement); return this.lines; }
    statement(statement) {
        switch (statement.kind) {
            case "declaration":
                this.lines.push(`${statement.name} = ${this.expression(statement.initializer)}`);
                break;
            case "assignment":
                this.lines.push(`${statement.name} = ${this.expression(statement.value)}`);
                break;
            case "print":
                this.lines.push(`print ${this.expression(statement.expression)}`);
                break;
            case "block":
                for (const child of statement.statements)
                    this.statement(child);
                break;
            case "if": {
                const otherwise = this.newLabel();
                const end = this.newLabel();
                this.lines.push(`ifFalse ${this.expression(statement.condition)} goto ${otherwise}`);
                statement.thenBranch.forEach(child => this.statement(child));
                if (statement.elseBranch) {
                    this.lines.push(`goto ${end}`, `${otherwise}:`);
                    statement.elseBranch.forEach(child => this.statement(child));
                    this.lines.push(`${end}:`);
                }
                else
                    this.lines.push(`${otherwise}:`);
                break;
            }
            case "while": {
                const start = this.newLabel();
                const end = this.newLabel();
                this.lines.push(`${start}:`, `ifFalse ${this.expression(statement.condition)} goto ${end}`);
                statement.body.forEach(child => this.statement(child));
                this.lines.push(`goto ${start}`, `${end}:`);
            }
        }
    }
    expression(expression) {
        if (expression.kind === "literal")
            return typeof expression.value === "string" ? JSON.stringify(expression.value) : String(expression.value);
        if (expression.kind === "variable")
            return expression.name;
        if (expression.kind === "unary") {
            const target = this.newTemporary();
            this.lines.push(`${target} = ${expression.operator}${this.expression(expression.operand)}`);
            return target;
        }
        const left = this.expression(expression.left);
        const right = this.expression(expression.right);
        const target = this.newTemporary();
        this.lines.push(`${target} = ${left} ${expression.operator} ${right}`);
        return target;
    }
    newTemporary() { return `t${++this.temporary}`; }
    newLabel() { return `L${++this.label}`; }
}
class Interpreter {
    constructor() {
        this.scopes = [new Map()];
        this.output = [];
        this.steps = 0;
    }
    run(statements) { for (const statement of statements)
        this.execute(statement); return this.output; }
    execute(statement) {
        if (++this.steps > 25000)
            throw new MiniLangError("Execution stopped after 25,000 statements to prevent an infinite loop.", "Execution", statement.line, statement.column);
        switch (statement.kind) {
            case "declaration": {
                const value = this.evaluate(statement.initializer);
                this.scopes[this.scopes.length - 1].set(statement.name, value);
                return;
            }
            case "assignment": {
                const scope = this.findScope(statement.name);
                if (!scope)
                    throw new MiniLangError(`Variable '${statement.name}' is not declared.`, "Execution", statement.line, statement.column);
                scope.set(statement.name, this.evaluate(statement.value));
                return;
            }
            case "print":
                this.output.push(String(this.evaluate(statement.expression).value));
                return;
            case "block":
                this.withScope(statement.statements);
                return;
            case "if":
                if (this.evaluate(statement.condition).value === true)
                    this.withScope(statement.thenBranch);
                else if (statement.elseBranch)
                    this.withScope(statement.elseBranch);
                return;
            case "while":
                while (this.evaluate(statement.condition).value === true) {
                    if (++this.steps > 25000)
                        throw new MiniLangError("Execution stopped after 25,000 statements to prevent an infinite loop.", "Execution", statement.line, statement.column);
                    this.withScope(statement.body);
                }
        }
    }
    evaluate(expression) {
        if (expression.kind === "literal")
            return { value: expression.value, type: expression.valueType };
        if (expression.kind === "variable") {
            const scope = this.findScope(expression.name);
            const binding = scope?.get(expression.name);
            if (!binding)
                throw new MiniLangError(`Variable '${expression.name}' is not available in this scope.`, "Execution", expression.line, expression.column);
            return binding;
        }
        if (expression.kind === "unary") {
            const operand = this.evaluate(expression.operand);
            return expression.operator === "!"
                ? { value: !operand.value, type: "boolean" }
                : { value: expression.operator === "-" ? -Number(operand.value) : Number(operand.value), type: operand.type };
        }
        const left = this.evaluate(expression.left);
        if (expression.operator === "&&" && left.value === false)
            return { value: false, type: "boolean" };
        if (expression.operator === "||" && left.value === true)
            return { value: true, type: "boolean" };
        const right = this.evaluate(expression.right);
        const a = left.value;
        const b = right.value;
        switch (expression.operator) {
            case "+": return typeof a === "string" ? { value: a + String(b), type: "string" } : this.numeric(Number(a) + Number(b));
            case "-": return this.numeric(Number(a) - Number(b));
            case "*": return this.numeric(Number(a) * Number(b));
            case "/":
                if (Number(b) === 0)
                    throw new MiniLangError("Division by zero.", "Execution", expression.line, expression.column);
                return this.numeric(Number(a) / Number(b));
            case "%":
                if (Number(b) === 0)
                    throw new MiniLangError("Remainder by zero.", "Execution", expression.line, expression.column);
                return this.numeric(Number(a) % Number(b));
            case "==": return { value: a === b, type: "boolean" };
            case "!=": return { value: a !== b, type: "boolean" };
            case ">": return { value: a > b, type: "boolean" };
            case ">=": return { value: a >= b, type: "boolean" };
            case "<": return { value: a < b, type: "boolean" };
            case "<=": return { value: a <= b, type: "boolean" };
            case "&&": return { value: Boolean(a) && Boolean(b), type: "boolean" };
            case "||": return { value: Boolean(a) || Boolean(b), type: "boolean" };
            default: throw new MiniLangError(`Unknown operator '${expression.operator}'.`, "Execution", expression.line, expression.column);
        }
    }
    numeric(value) { return { value, type: Number.isInteger(value) ? "integer" : "float" }; }
    withScope(statements) {
        this.scopes.push(new Map());
        for (const statement of statements)
            this.execute(statement);
        this.scopes.pop();
    }
    findScope(name) {
        for (let index = this.scopes.length - 1; index >= 0; index--)
            if (this.scopes[index].has(name))
                return this.scopes[index];
        return undefined;
    }
}
export function compileMiniLang(source) {
    const result = {
        tokens: [], ast: null, optimizedAst: null, tac: [], optimizedTac: [], output: [], error: null,
        stats: { tokenCount: 0, statementCount: 0, folded: 0, unreachable: 0 },
    };
    try {
        if (source.length > 20000)
            throw new MiniLangError("Source is limited to 20,000 characters.", "Lexical", 1, 1);
        result.tokens = new Lexer(source).scan();
        result.stats.tokenCount = result.tokens.filter(token => token.kind !== "eof").length;
        result.ast = new Parser(result.tokens).parse();
        result.stats.statementCount = result.ast.length;
        new SemanticAnalyzer().analyze(result.ast);
        result.tac = new TacGenerator().generate(result.ast);
        result.optimizedAst = optimizeStatements(result.ast, result.stats);
        result.optimizedTac = new TacGenerator().generate(result.optimizedAst);
        result.output = new Interpreter().run(result.optimizedAst);
    }
    catch (error) {
        if (error instanceof MiniLangError)
            result.error = { phase: error.phase, message: error.message, line: error.line, column: error.column };
        else
            result.error = { phase: "Compiler", message: error instanceof Error ? error.message : String(error), line: 1, column: 1 };
    }
    return result;
}
