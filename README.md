
# 🧠 **miniLang**

> A Fast, LLVM-Compiled Programming Language with Static Typing and Inference

---

![Language](https://img.shields.io/badge/language-miniLang-blueviolet)
![Backend](https://img.shields.io/badge/backend-LLVM%2010%2B-orange)
![Parser](https://img.shields.io/badge/parser-Lark-blue)
![Performance](https://img.shields.io/badge/performance-112x%20faster%20than%20Python-brightgreen)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

---

## 📖 Description

**miniLang** is a compiled programming language designed for speed and efficiency. It leverages static typing with inference and compiles to **LLVM IR** using a custom compiler written in Python.

---

## ✨ Features

- ⚡ **Blazing Fast Performance:** Achieves up to **112x speedup** compared to Python.
- 💪 **Static Typing with Inference:** Catch type errors at compile time while writing less boilerplate.
- 📦 **Core Data Types:** Supports `int` (32-bit), `float` (double), `str` (string), and `bool` (boolean).
- 🧩 **Familiar Syntax:** Combines intuitive syntax with a unique block structure using brackets `[]`.
- 🚀 **LLVM Backend:** Leverages LLVM for native performance and optimization.

---

## 📈 Performance

> We benchmarked `miniLang` by summing integers up to 1 million.

- **Python:** 3.47 seconds  
- **miniLang:** 0.031 seconds  
- ✅ **Result:** ~112x faster than Python

---

## 🧾 Language Syntax

### 🧠 Variable Declaration
```miniLang
let x = 42 int;
let name = "Hello" str;
```

### 🔁 Control Flow
```miniLang
if [x > 10] [
    print["x is big"];
] else [
    print["x is small"];
]

while [x > 0] [
    print[x];
    x = x - 1;
]
```

### 📤 Printing
```miniLang
print["Hello, world!"];
print[x, y];
```

### ⚙️ Operators

- Arithmetic: `+`, `-`, `*`, `/`, `%`
- Comparison: `==`, `!=`, `<`, `>`, `<=`, `>=`
- Logical: `&&`, `||`, `!`
- Unary: `+`, `-`

### 💬 Comments
```miniLang
// This is a comment
```

---

## ⚙️ Installation & Setup

### 🔧 Requirements

- Python 3.7+
- LLVM 10+
- Install dependencies:
  ```bash
  pip install lark llvmlite
  ```

### 🖥️ Supported Platforms

- ✅ Windows
- ✅ macOS
- ✅ Linux

---

## 🚀 Usage Guide

1. Write your program in a `.lang` file.
2. Compile it to LLVM IR:
   ```bash
   python llvm_compiler.py example.lang > output.ll
   ```
3. Run the compiled IR:
   ```bash
   lli output.ll
   ```

---

## 📂 Example Programs

### 🔹 Hello World
```miniLang
print["Hello, world!"];
```

### 🔹 Factorial
```miniLang
let n = 5 int;
let result = 1 int;

while [n > 1] [
    result = result * n;
    n = n - 1;
]
print["Factorial is", result];
```

### 🔹 Fibonacci
```miniLang
let a = 0 int;
let b = 1 int;
let i = 0 int;

while [i < 10] [
    print[a];
    let temp = a int;
    a = b;
    b = temp + b;
    i = i + 1;
]
```

---

## 🏗️ Architecture Overview

```
Source Code (.lang)
       ↓
  [Lark Parser → AST]
       ↓
[LLVM IR Generation via llvmlite]
       ↓
  [Native Execution via lli]
```

---

## 🛡️ Error Handling

- Compile-time detection of:
  - Type mismatches
  - Undeclared variables
  - Invalid syntax
- Clear, informative error messages

---

## 🗂 Repository Structure

```
miniLang/
├── grammar.lark         # Language grammar definition
├── llvm_compiler.py     # Compiler: source → LLVM IR
├── interpreter.py       # Optional interpreter (WIP)
├── examples/            # Example programs in miniLang
└── README.md            # Documentation
```

---

## 🤝 Contributing

Contributions are welcome! Whether it's extending the language, improving the compiler, or adding features — feel free to fork, branch, and PR.

---

## 📜 License

MIT License. See `LICENSE` for details.

---

> miniLang — Minimal syntax. Maximum speed.
