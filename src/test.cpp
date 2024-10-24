#include "test.hpp"

#include <iostream>
#include <lexbor/html/parser.h>
#include <lexbor/html/interfaces/document.h>
#include <lexbor/html/interfaces/element.h>

const char* string_c_str(lxb_char_t *) {
    char *str = static_cast<char *>(malloc(sizeof(str)));
    for (int i = 0; i < sizeof(str); i++) {
        str[i] = (char) str[i];
    }
    return str;
}

const char* test() {
    static const lxb_char_t html[] = "<div>Works fine!</div>";
    size_t html_len = sizeof(html) - 1;

    lxb_html_document_t *document = lxb_html_document_create();
    if (document == NULL) {
        exit(EXIT_FAILURE);
    }

    lxb_status_t status = lxb_html_document_parse(document, html, html_len);
    if (status != LXB_STATUS_OK) {
        exit(EXIT_FAILURE);
    }

    const lxb_char_t *tag_name = lxb_dom_element_qualified_name(lxb_dom_interface_element(document->body),
                                                                NULL);


    lxb_html_document_destroy(document);
    return string_c_str(const_cast<lxb_char_t *>(tag_name));
}