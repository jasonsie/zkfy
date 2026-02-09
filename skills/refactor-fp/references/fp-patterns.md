# Functional Programming Patterns Reference

## Advanced Array Transformations

### flatMap: Map and flatten in one step

```typescript
// BEFORE: map + flat
const nested = users.map((u) => u.orders);
const orders = nested.flat();

// AFTER: flatMap
const orders = users.flatMap((u) => u.orders);
```

### find with default using nullish coalescing

```typescript
// BEFORE: Conditional assignment
const user = users.find((u) => u.id === id);
const name = user ? user.name : 'Anonymous';

// AFTER: Optional chaining + nullish coalescing
const name = users.find((u) => u.id === id)?.name ?? 'Anonymous';
```

### groupBy pattern

```typescript
// Utility function
const groupBy = <T, K extends string | number>(
  arr: T[],
  keyFn: (item: T) => K
): Record<K, T[]> =>
  arr.reduce((acc, item) => {
    const key = keyFn(item);
    return {
      ...acc,
      [key]: [...(acc[key] || []), item],
    };
  }, {} as Record<K, T[]>);

// Usage
const byDepartment = groupBy(employees, (e) => e.department);
```

### partition: Split array by predicate

```typescript
const partition = <T>(arr: T[], predicate: (item: T) => boolean): [T[], T[]] =>
  arr.reduce(
    ([pass, fail], item) =>
      predicate(item) ? [[...pass, item], fail] : [pass, [...fail, item]],
    [[], []] as [T[], T[]]
  );

// Usage
const [active, inactive] = partition(users, (u) => u.isActive);
```

### zip: Combine two arrays element-wise

```typescript
const zip = <A, B>(a: A[], b: B[]): [A, B][] =>
  a.map((item, i) => [item, b[i]]);

const zipWith = <A, B, C>(a: A[], b: B[], fn: (a: A, b: B) => C): C[] =>
  a.map((item, i) => fn(item, b[i]));

// Usage
const pairs = zip(names, ages); // [['Alice', 30], ['Bob', 25]]
const records = zipWith(names, ages, (name, age) => ({ name, age }));
```

## Function Composition Patterns

### Compose (right-to-left)

```typescript
const compose =
  <T>(...fns: Array<(arg: T) => T>) =>
  (x: T): T =>
    fns.reduceRight((v, f) => f(v), x);

// Usage: read bottom-to-top
const process = compose(
  capitalize, // 3. Capitalize
  trim, // 2. Trim whitespace
  toLowerCase // 1. First lowercase
);
```

### Pipe (left-to-right, more readable)

```typescript
const pipe =
  <T>(...fns: Array<(arg: T) => T>) =>
  (x: T): T =>
    fns.reduce((v, f) => f(v), x);

// Usage: read top-to-bottom
const process = pipe(
  toLowerCase, // 1. First lowercase
  trim, // 2. Trim whitespace
  capitalize // 3. Capitalize
);
```

### Type-safe pipe with different types

```typescript
// Overloaded pipe for type safety
function pipe<A, B>(a: A, ab: (a: A) => B): B;
function pipe<A, B, C>(a: A, ab: (a: A) => B, bc: (b: B) => C): C;
function pipe<A, B, C, D>(
  a: A,
  ab: (a: A) => B,
  bc: (b: B) => C,
  cd: (c: C) => D
): D;
function pipe(a: unknown, ...fns: Function[]): unknown {
  return fns.reduce((v, f) => f(v), a);
}

// Usage with type inference
const result = pipe(
  '  HELLO WORLD  ',
  (s) => s.trim(),
  (s) => s.toLowerCase(),
  (s) => s.split(' '),
  (words) => words.length
); // result: number
```

## Currying and Partial Application

### Manual currying

```typescript
// BEFORE: Function with multiple parameters
const add = (a: number, b: number, c: number) => a + b + c;
add(1, 2, 3);

// AFTER: Curried version
const addCurried = (a: number) => (b: number) => (c: number) => a + b + c;
addCurried(1)(2)(3);

// Partial application
const add5 = addCurried(5);
const add5and10 = add5(10);
add5and10(3); // 18
```

### Generic curry utility

```typescript
const curry2 =
  <A, B, R>(fn: (a: A, b: B) => R) =>
  (a: A) =>
  (b: B) =>
    fn(a, b);

const curry3 =
  <A, B, C, R>(fn: (a: A, b: B, c: C) => R) =>
  (a: A) =>
  (b: B) =>
  (c: C) =>
    fn(a, b, c);

// Usage
const multiply = curry2((a: number, b: number) => a * b);
const double = multiply(2);
double(5); // 10
```

## Immutable Data Structure Patterns

### Deep clone for nested updates

```typescript
const updatePath = <T extends object>(
  obj: T,
  path: string[],
  value: unknown
): T => {
  if (path.length === 0) return value as T;
  const [head, ...tail] = path;
  return {
    ...obj,
    [head]: updatePath(
      (obj as Record<string, unknown>)[head] as object,
      tail,
      value
    ),
  } as T;
};

// Usage
const updated = updatePath(user, ['address', 'city'], 'New York');
```

### Lens pattern for nested access

```typescript
interface Lens<S, A> {
  get: (s: S) => A;
  set: (a: A, s: S) => S;
}

const lens = <S, A>(
  getter: (s: S) => A,
  setter: (a: A, s: S) => S
): Lens<S, A> => ({
  get: getter,
  set: setter,
});

const over = <S, A>(l: Lens<S, A>, fn: (a: A) => A, s: S): S =>
  l.set(fn(l.get(s)), s);

// Usage
const nameLens = lens<User, string>(
  (u) => u.name,
  (name, u) => ({ ...u, name })
);

const upperName = over(nameLens, (s) => s.toUpperCase(), user);
```

## Async Functional Patterns

### Promise.all with map

```typescript
// BEFORE: Sequential async
const results = [];
for (const id of ids) {
  const result = await fetchUser(id);
  results.push(result);
}

// AFTER: Parallel async
const results = await Promise.all(ids.map(fetchUser));
```

### Async pipe

```typescript
const asyncPipe =
  <T>(...fns: Array<(arg: T) => T | Promise<T>>) =>
  async (x: T): Promise<T> => {
    let result = x;
    for (const fn of fns) {
      result = await fn(result);
    }
    return result;
  };

// Usage
const processUser = asyncPipe(fetchUser, validateUser, enrichUser, saveUser);
```

### Async Result pattern

```typescript
type AsyncResult<T, E = Error> = Promise<Result<T, E>>;

const tryCatch = async <T>(fn: () => Promise<T>): AsyncResult<T> => {
  try {
    return ok(await fn());
  } catch (e) {
    return err(e instanceof Error ? e : new Error(String(e)));
  }
};

// Usage
const fetchData = (): AsyncResult<Data> =>
  tryCatch(() => fetch('/api').then((r) => r.json()));
```

## Pattern Matching Helpers

### Match expression

```typescript
const match = <T extends string | number, R>(
  value: T,
  patterns: Record<T, () => R>,
  defaultFn?: () => R
): R => {
  const handler = patterns[value] ?? defaultFn;
  if (!handler) throw new Error(`No match for ${value}`);
  return handler();
};

// Usage
const message = match(status, {
  loading: () => 'Please wait...',
  success: () => 'Done!',
  error: () => 'Something went wrong',
});
```

### Type-safe exhaustive matching

```typescript
const assertNever = (x: never): never => {
  throw new Error(`Unexpected value: ${x}`);
};

type Status = 'idle' | 'loading' | 'success' | 'error';

const getMessage = (status: Status): string => {
  switch (status) {
    case 'idle':
      return 'Ready';
    case 'loading':
      return 'Loading...';
    case 'success':
      return 'Complete';
    case 'error':
      return 'Failed';
    default:
      return assertNever(status);
  }
};
```

## Memoization

### Simple memoize

```typescript
const memoize = <A, R>(fn: (arg: A) => R): ((arg: A) => R) => {
  const cache = new Map<A, R>();
  return (arg: A): R => {
    if (cache.has(arg)) return cache.get(arg)!;
    const result = fn(arg);
    cache.set(arg, result);
    return result;
  };
};

// Usage
const expensiveCalculation = memoize((n: number) => {
  // Expensive computation
  return fibonacci(n);
});
```

### Memoize with multiple arguments

```typescript
const memoizeMulti = <Args extends unknown[], R>(
  fn: (...args: Args) => R
): ((...args: Args) => R) => {
  const cache = new Map<string, R>();
  return (...args: Args): R => {
    const key = JSON.stringify(args);
    if (cache.has(key)) return cache.get(key)!;
    const result = fn(...args);
    cache.set(key, result);
    return result;
  };
};
```

## Debugging Functional Code

### Tap: Inspect without modifying

```typescript
const tap =
  <T>(fn: (x: T) => void) =>
  (x: T): T => {
    fn(x);
    return x;
  };

// Usage in pipe
const result = pipe(
  data,
  transform1,
  tap((x) => console.log('After transform1:', x)),
  transform2,
  tap((x) => console.log('After transform2:', x)),
  transform3
);
```

### Trace: Named tap for debugging

```typescript
const trace =
  <T>(label: string) =>
  (x: T): T => {
    console.log(`[${label}]`, x);
    return x;
  };

// Usage
const result = pipe(
  data,
  trace('input'),
  filter(isValid),
  trace('after filter'),
  map(transform),
  trace('after map')
);
```
