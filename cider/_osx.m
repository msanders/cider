#import <AppKit/AppKit.h>
#include <Python.h>
#import <errno.h>

static PyObject *setIcon(NSString *filePath, NSString *iconPath)
{
    NSFileManager *fileManager = [NSFileManager defaultManager];
    NSWorkspace *workspace = [NSWorkspace sharedWorkspace];
    NSArray *paths = @[filePath];
    if (iconPath) {
        paths = [paths arrayByAddingObject:iconPath];
    }

    for (NSString *path in paths) {
        if (![fileManager fileExistsAtPath:path]) {
            errno = ENOENT;
            PyErr_SetFromErrnoWithFilename(PyExc_OSError, [path UTF8String]);
            return NULL;
        }
    }

    NSImage *icon = [[NSImage alloc] initByReferencingFile:iconPath];
    [workspace setIcon:icon forFile:filePath options:0];

    Py_RETURN_NONE;
}

static PyObject *py_pathForApp(PyObject *self, PyObject *args)
{
    const char *appNameBuf;
    if (!PyArg_ParseTuple(args, "s", &appNameBuf)) {
        return NULL;
    }

    @autoreleasepool {
        NSString *appName = [NSString stringWithUTF8String:appNameBuf];
        NSString *appPath = [[NSWorkspace sharedWorkspace] fullPathForApplication:appName];
        if (appPath) {
            return PyUnicode_FromString([appPath UTF8String]);
        }
    }

    Py_RETURN_NONE;
}

static PyObject *py_setIcon(PyObject *self, PyObject *args)
{
    const char *filePathBuf;
    const char *iconPathBuf;
    if (!PyArg_ParseTuple(args, "ss", &filePathBuf, &iconPathBuf)) {
        return NULL;
    }

    @autoreleasepool {
        NSString *filePath = [NSString stringWithUTF8String:filePathBuf];
        NSString *iconPath = [NSString stringWithUTF8String:iconPathBuf];
        return setIcon(filePath, iconPath);
    }
}

static PyObject *py_removeIcon(PyObject *self, PyObject *args)
{
    const char *filePathBuf;
    if (!PyArg_ParseTuple(args, "s", &filePathBuf)) {
        return NULL;
    }

    @autoreleasepool {
        NSString *filePath = [NSString stringWithUTF8String:filePathBuf];
        return setIcon(filePath, nil);
    }
}

static PyMethodDef osx_methods[] = {
    {"path_for_app", py_pathForApp, METH_VARARGS},
    {"set_icon", py_setIcon, METH_VARARGS},
    {"remove_icon", py_removeIcon, METH_VARARGS},
    {NULL, NULL}
};

void init_osx(void)
{
    Py_InitModule("_osx", osx_methods);
}
