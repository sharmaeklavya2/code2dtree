'use strict';

const nodeAndFragClasses = ['node', 'nodeFrag', 'dtree'];

function checkBoxChangeHandler(ev) {
    if(ev.target.tagName.toLowerCase() === 'input' && ev.target.getAttribute('type') === 'checkbox') {
        const nodeId = ev.target.getAttribute('name');
        if(nodeId !== null && nodeId.startsWith('node')) {
            const nodeElem = document.getElementById(nodeId);
            selectNode(nodeElem, ev.target.checked);
            callUpwards(nodeElem, updateIsel, nodeAndFragClasses);
        }
    }
}

function selectNode(nodeElem, select) {
    if(select) {
        nodeElem.classList.add('sel');
    }
    else {
        nodeElem.classList.remove('sel');
    }
}

function updateIsel(nodeElem) {
    nodeElem.classList.remove('isel');
    if(nodeElem.classList.contains('sel')) {
        nodeElem.classList.add('isel');
    }
    else {
        for(const kidElem of nodeElem.children) {
            if(kidElem.classList.contains('isel')) {
                nodeElem.classList.add('isel');
                break;
            }
        }
    }
    if(nodeElem.classList.contains('ifNode')) {
        nodeElem.classList.remove('isel0');
        nodeElem.classList.remove('isel1');
        nodeElem.classList.remove('isel2');
        let trueSel = false, falseSel = false;
        for(const kidElem of nodeElem.children) {
            if(kidElem.classList.contains('isel')) {
                if(kidElem.classList.contains('ifTrue')) {
                    trueSel = true;
                }
                else if(kidElem.classList.contains('ifFalse')) {
                    falseSel = true;
                }
            }
        }
        if(trueSel) {
            if(falseSel) {
                nodeElem.classList.add('isel2');
            }
            else {
                nodeElem.classList.add('isel1');
            }
        }
        else if(falseSel) {
            nodeElem.classList.add('isel0');
        }
    }
}

function classListOverlap(list1, list2) {
    for(const x of list1) {
        for(const y of list2) {
            if(x == y) {
                return true;
            }
        }
    }
    return false;
}

function callUpwards(elem, f, classes) {
    while(elem !== null) {
        if(classListOverlap(elem.classList, classes)) {
            f(elem);
            elem = elem.parentElement;
        }
        else {
            break;
        }
    }
}

function callPostOrder(elem, f, classes) {
    if(classListOverlap(elem.classList, classes)) {
        for(const kid of elem.children) {
            callPostOrder(kid, f, classes);
        }
        f(elem);
    }
}

function initSel(dtreeElem) {
    for(const checkBoxElem of document.querySelectorAll('.dtree input[type="checkbox"]')) {
        const nodeId = checkBoxElem.getAttribute('name');
        if(nodeId !== null && nodeId.startsWith('node')) {
            const nodeElem = document.getElementById(nodeId);
            selectNode(nodeElem, checkBoxElem.checked);
        }
    }
    callPostOrder(dtreeElem, updateIsel, nodeAndFragClasses);
}

function main() {
    const dtreeList = document.getElementsByClassName('dtree');
    if(dtreeList.length !== 1) {
        throw Exception('there must be exactly one dtree.');
    }
    initSel(dtreeList[0]);
    dtreeList[0].addEventListener('change', checkBoxChangeHandler);
}

window.addEventListener('load', main);
