---
name: refactor-fp
description: This skill refactors imperative JavaScript/TypeScript code to functional programming patterns. Use when asked to convert loops to map/filter/reduce, eliminate mutation in favor of immutability, replace try/catch with functional error handling, or apply function composition. Triggers on requests mentioning "functional", "FP", "immutable", "pure functions", or "refactor to functional".
---

# Refactor to Functional Programming

## Overview

This skill transforms imperative JavaScript/TypeScript code into idiomatic functional programming patterns using vanilla JS/TS without external libraries. It covers three core transformation categories: loops to higher-order functions, mutation to immutability, and imperative error handling to functional patterns.

## Quick Reference

| Imperative Pattern               | Functional Equivalent                  |
| -------------------------------- | -------------------------------------- |
| `for` loop with push             | `map()`                                |
| `for` loop with conditional push | `filter()`                             |
| `for` loop accumulating value    | `reduce()`                             |
| Object mutation                  | Spread operator `{...obj}`             |
| Array mutation                   | `map()`, `filter()`, spread `[...arr]` |
| `try/catch` blocks               | Result types, Option pattern           |
| Nested conditionals              | Early returns, pattern matching        |
| `null` checks                    | Optional chaining, nullish coalescing  |

## Transformation Patterns

### 1. Loops to Higher-Order Functions

#### Map: Transform each element

```typescript
// BEFORE: Imperative loop
const doubled = [];
for (let i = 0; i < numbers.length; i++) {
  doubled.push(numbers[i] * 2);
}

// AFTER: Functional map
const doubled = numbers.map((n) => n * 2);
```

#### Filter: Select elements matching condition

```typescript
// BEFORE: Imperative loop with conditional
const adults = [];
for (const person of people) {
  if (person.age >= 18) {
    adults.push(person);
  }
}

// AFTER: Functional filter
const adults = people.filter((person) => person.age >= 18);
```

#### Reduce: Accumulate to single value

```typescript
// BEFORE: Imperative accumulation
let total = 0;
for (const item of items) {
  total += item.price * item.quantity;
}

// AFTER: Functional reduce
const total = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
```

#### Chaining: Combine operations with pipe pattern

```typescript
// BEFORE: Multiple loops
const temps = [];
for (const city of cities) {
  if (city.country === 'USA') {
    temps.push(city.temp);
  }
}
let sum = 0;
for (const t of temps) {
  sum += t;
}
const avg = sum / temps.length;

// AFTER: Functional chain
const usaCities = cities.filter((c) => c.country === 'USA');
const avgTemp =
  usaCities.reduce((sum, c) => sum + c.temp, 0) / usaCities.length;

// BETTER: Custom pipe function for complex chains
const pipe =
  (...fns) =>
  (x) =>
    fns.reduce((v, f) => f(v), x);

const getAvgUSATemp = pipe(
  (cities) => cities.filter((c) => c.country === 'USA'),
  (usaCities) => usaCities.map((c) => c.temp),
  (temps) => temps.reduce((a, b) => a + b, 0) / temps.length
);
```

### 2. Mutation to Immutability

#### Object updates

```typescript
// BEFORE: Mutation
function updateUser(user, name) {
  user.name = name;
  return user;
}

// AFTER: Immutable spread
function updateUser(user, name) {
  return { ...user, name };
}

// Nested object updates
function updateAddress(user, city) {
  return {
    ...user,
    address: { ...user.address, city },
  };
}
```

#### Array operations

```typescript
// BEFORE: Mutating array
function addItem(items, item) {
  items.push(item);
  return items;
}

function removeItem(items, id) {
  const index = items.findIndex((i) => i.id === id);
  items.splice(index, 1);
  return items;
}

// AFTER: Immutable array operations
function addItem(items, item) {
  return [...items, item];
}

function removeItem(items, id) {
  return items.filter((item) => item.id !== id);
}

function updateItem(items, id, updates) {
  return items.map((item) => (item.id === id ? { ...item, ...updates } : item));
}
```

#### Map/Set operations

```typescript
// BEFORE: Mutating Map
function setKey(map, key, value) {
  map.set(key, value);
  return map;
}

// AFTER: Immutable Map
function setKey(map, key, value) {
  return new Map(map).set(key, value);
}

// Immutable Set
function addToSet(set, value) {
  return new Set(set).add(value);
}
```

### 3. Error Handling to Functional Patterns

#### Result type pattern (Either-like)

```typescript
// Define Result type
type Result<T, E = Error> = { ok: true; value: T } | { ok: false; error: E };

const ok = <T>(value: T): Result<T, never> => ({ ok: true, value });
const err = <E>(error: E): Result<never, E> => ({ ok: false, error });

// BEFORE: Try/catch
function divide(a: number, b: number): number {
  if (b === 0) throw new Error('Division by zero');
  return a / b;
}

try {
  const result = divide(10, 0);
  console.log(result);
} catch (e) {
  console.error(e.message);
}

// AFTER: Result type
function divide(a: number, b: number): Result<number, string> {
  if (b === 0) return err('Division by zero');
  return ok(a / b);
}

const result = divide(10, 0);
if (result.ok) {
  console.log(result.value);
} else {
  console.error(result.error);
}
```

#### Option type pattern (Maybe-like)

```typescript
// Define Option type
type Option<T> = { some: true; value: T } | { some: false };

const some = <T>(value: T): Option<T> => ({ some: true, value });
const none: Option<never> = { some: false };

// BEFORE: Null checks
function findUser(id: string): User | null {
  const user = users.find((u) => u.id === id);
  return user || null;
}

const user = findUser('123');
if (user !== null) {
  console.log(user.name);
}

// AFTER: Option type
function findUser(id: string): Option<User> {
  const user = users.find((u) => u.id === id);
  return user ? some(user) : none;
}

const userOpt = findUser('123');
if (userOpt.some) {
  console.log(userOpt.value.name);
}
```

#### Chaining Result/Option with map and flatMap

```typescript
// Result utilities
const mapResult = <T, U, E>(
  result: Result<T, E>,
  fn: (value: T) => U
): Result<U, E> => (result.ok ? ok(fn(result.value)) : result);

const flatMapResult = <T, U, E>(
  result: Result<T, E>,
  fn: (value: T) => Result<U, E>
): Result<U, E> => (result.ok ? fn(result.value) : result);

// Usage: Chain operations that may fail
const parseNumber = (s: string): Result<number, string> => {
  const n = Number(s);
  return isNaN(n) ? err('Not a number') : ok(n);
};

const safeDivide = (a: number, b: number): Result<number, string> =>
  b === 0 ? err('Division by zero') : ok(a / b);

// Compose fallible operations
const compute = (input: string): Result<number, string> =>
  flatMapResult(parseNumber(input), (n) => safeDivide(100, n));
```

## Refactoring Workflow

To refactor imperative code to functional style:

1. **Identify mutation points** - Find variables being reassigned or objects/arrays being modified
2. **Categorize the pattern** - Determine if it's a loop, mutation, or error handling pattern
3. **Apply transformation** - Use the corresponding functional pattern from references
4. **Verify immutability** - Ensure no side effects; inputs unchanged, new values returned
5. **Simplify with composition** - Chain operations using pipe pattern if multiple transformations

## Common Pitfalls to Avoid

- **Avoid** `forEach` when a return value is needed (use `map` or `reduce`)
- **Avoid** `reduce` for simple filtering (use `filter` instead)
- **Avoid** nested ternaries deeper than 2 levels (extract to functions)
- **Avoid** mutating function parameters even with spread (clone at function entry)

## Resources

For detailed patterns and additional examples, see `references/fp-patterns.md`.
