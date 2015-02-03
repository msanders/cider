#import <AppKit/AppKit.h>
#include <Python.h>
#include <errno.h>

static PyObject *setIcon(NSString *filePath, NSString *iconPath)
{
    NSFileManager *fileManager = [NSFileManager defaultManager];
    NSWorkspace *workspace = [NSWorkspace sharedWorkspace];
    NSArray *paths = [NSArray arrayWithObject:filePath];
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

static void setPyErrorFromNSError(NSError *error)
{
    NSArray *keys = [NSArray arrayWithObjects:NSLocalizedDescriptionKey,
                                              NSLocalizedFailureReasonErrorKey, nil];
    NSMutableArray *errors = [NSMutableArray arrayWithCapacity:keys.count];
    for (NSString *key in keys) {
        NSString *value = [error.userInfo objectForKey:key];
        if (value) {
            [errors addObject:value];
        }
    }

    PyErr_SetString(PyExc_OSError, [[errors componentsJoinedByString:@" "] UTF8String]);
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

static PyObject *py_moveToTrash(PyObject *self, PyObject *args)
{
    const char *filePathBuf;
    if (!PyArg_ParseTuple(args, "s", &filePathBuf)) {
        return NULL;
    }

    @autoreleasepool {
        NSString *filePath = [NSString stringWithUTF8String:filePathBuf];
        NSURL *fileURL = [NSURL fileURLWithPath:filePath];
        NSURL *outURL = nil;
        NSError *error = nil;
        if (![[NSFileManager defaultManager] trashItemAtURL:fileURL resultingItemURL:&outURL error:&error]) {
            setPyErrorFromNSError(error);
            return NULL;
        }

        return PyUnicode_FromString([outURL.path UTF8String]);
    }
}

static PyMethodDef osx_methods[] = {
    {"path_for_app", py_pathForApp, METH_VARARGS},
    {"set_icon", py_setIcon, METH_VARARGS},
    {"remove_icon", py_removeIcon, METH_VARARGS},
    {"move_to_trash", py_moveToTrash, METH_VARARGS},
    {NULL, NULL}
};

#if PY_MAJOR_VERSION >= 3

static struct PyModuleDef osxdef = {
    PyModuleDef_HEAD_INIT,
    "_osx",
    NULL,
    0,
    osx_methods,
    NULL,
    NULL,
    NULL,
    NULL
};

PyObject *PyInit__osx(void)
#else
void init_osx(void)
#endif
{
#if PY_MAJOR_VERSION >= 3
    return PyModule_Create(&osxdef);
#else
    Py_InitModule("_osx", osx_methods);
#endif
}
