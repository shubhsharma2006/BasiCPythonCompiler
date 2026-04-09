from __future__ import annotations

from compiler.ir.cfg import BranchTerminator, CFGFunction, JumpTerminator


def block_map(function: CFGFunction) -> dict[str, object]:
    return {block.name: block for block in function.blocks}


def reachable_block_names(function: CFGFunction) -> set[str]:
    blocks = block_map(function)
    if function.entry_block not in blocks:
        return set()

    seen: set[str] = set()
    stack = [function.entry_block]
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        block = blocks[name]
        stack.extend(sorted(block.successors - seen))
    return seen


def reverse_post_order(function: CFGFunction) -> list[str]:
    blocks = block_map(function)
    if function.entry_block not in blocks:
        return []

    seen: set[str] = set()
    order: list[str] = []

    def dfs(name: str) -> None:
        if name in seen:
            return
        seen.add(name)
        for successor in sorted(blocks[name].successors):
            dfs(successor)
        order.append(name)

    dfs(function.entry_block)
    order.reverse()
    return order


def compute_dominators(function: CFGFunction) -> dict[str, set[str]]:
    blocks = block_map(function)
    order = reverse_post_order(function)
    if not order:
        return {}

    all_blocks = set(order)
    dominators: dict[str, set[str]] = {}
    for name in order:
        if name == function.entry_block:
            dominators[name] = {name}
        else:
            dominators[name] = set(all_blocks)

    changed = True
    while changed:
        changed = False
        for name in order[1:]:
            predecessors = blocks[name].predecessors
            if not predecessors:
                new_dom = {name}
            else:
                pred_sets = [dominators[pred] for pred in predecessors if pred in dominators]
                new_dom = set.intersection(*pred_sets) if pred_sets else set()
                new_dom.add(name)
            if new_dom != dominators[name]:
                dominators[name] = new_dom
                changed = True

    return dominators


def rebuild_edges(function: CFGFunction) -> None:
    blocks = block_map(function)
    for block in function.blocks:
        block.predecessors.clear()
        block.successors.clear()

    for block in function.blocks:
        terminator = block.terminator
        if isinstance(terminator, JumpTerminator):
            block.successors.add(terminator.target)
            if terminator.target in blocks:
                blocks[terminator.target].predecessors.add(block.name)
        elif isinstance(terminator, BranchTerminator):
            for target in (terminator.true_target, terminator.false_target):
                block.successors.add(target)
                if target in blocks:
                    blocks[target].predecessors.add(block.name)
