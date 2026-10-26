export function one(a) { return a; }
const two = (a, b) => {
  if (a && b) { return 1; }
  for (const x of a) { if (x) { continue; } }
  return a ? b : null;
};
class C {
  method(x) {
    switch (x) { case 1: return 1; case 2: return 2; }
    try { x(); } catch (e) { return e; }
  }
}
