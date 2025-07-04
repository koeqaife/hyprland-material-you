#include <gtk/gtk.h>
#include <stdlib.h>

static void
on_close_clicked(GtkButton *button, gpointer user_data)
{
    (void)button;
    GtkWindow *win = GTK_WINDOW(user_data);
    gtk_window_destroy(win);
}

static void
activate(GtkApplication *app, gpointer user_data)
{
    int exit_code = GPOINTER_TO_INT(user_data);
    char *desc_text = g_strdup_printf(
        "The UI crashed with exit code %d. A crash log was saved.\nTry restarting from terminal.",
        exit_code);

    GtkWidget *win = gtk_application_window_new(app);
    gtk_widget_add_css_class(GTK_WIDGET(win), "hypryou-crashed");
    gtk_window_set_title(GTK_WINDOW(win), "HyprYou crashed...");
    gtk_window_set_default_size(GTK_WINDOW(win), 450, 150);
    gtk_window_set_resizable(GTK_WINDOW(win), FALSE);

    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);
    gtk_window_set_child(GTK_WINDOW(win), box);

    GtkWidget *title = gtk_label_new(
        "HyprYou crashed...");
    gtk_label_set_wrap(GTK_LABEL(title), TRUE);
    gtk_label_set_justify(GTK_LABEL(title), GTK_JUSTIFY_CENTER);
    gtk_label_set_xalign(GTK_LABEL(title), 0);
    gtk_widget_add_css_class(GTK_WIDGET(title), "title");
    gtk_box_append(GTK_BOX(box), title);

    GtkWidget *description = gtk_label_new(desc_text);
    gtk_label_set_wrap(GTK_LABEL(description), TRUE);
    gtk_label_set_justify(GTK_LABEL(description), GTK_JUSTIFY_LEFT);
    gtk_label_set_xalign(GTK_LABEL(description), 0);
    gtk_widget_add_css_class(GTK_WIDGET(description), "description");
    gtk_box_append(GTK_BOX(box), description);
    g_free(desc_text);

    GtkWidget *button = gtk_button_new_with_label("OK");
    gtk_widget_set_halign(button, GTK_ALIGN_END);
    g_signal_connect(button, "clicked", G_CALLBACK(on_close_clicked), win);
    gtk_box_append(GTK_BOX(box), button);

    GtkCssProvider *provider = gtk_css_provider_new();
    // Minimum style just in case if gtk4 theme is not set
    gtk_css_provider_load_from_string(provider,
                                      ".title { font-size: 20px; font-weight: 400; }"
                                      ".description { font-size: 16px; font-weight: 300; }"
                                      ".hypryou-crashed { padding: 20px; }");

    gtk_style_context_add_provider_for_display(
        gdk_display_get_default(),
        GTK_STYLE_PROVIDER(provider),
        GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);

    gtk_window_present(GTK_WINDOW(win));
}

int main(int argc, char **argv)
{
    GError *error = NULL;
    GOptionContext *context;
    int exit_code = -1;

    GOptionEntry entries[] = {
        {"code", 'c', 0, G_OPTION_ARG_INT, &exit_code, "Exit code to display", "CODE"},
        {NULL}};

    context = g_option_context_new(NULL);
    g_option_context_add_main_entries(context, entries, NULL);

    if (!g_option_context_parse(context, &argc, &argv, &error))
    {
        g_printerr("Failed to parse options: %s\n", error->message);
        g_clear_error(&error);
        g_option_context_free(context);
        return 1;
    }
    g_option_context_free(context);

    GtkApplication *app = gtk_application_new("com.koeqaife.hypryou.crashed", G_APPLICATION_DEFAULT_FLAGS);

    g_signal_connect(app, "activate", G_CALLBACK(activate), GINT_TO_POINTER(exit_code));

    int status = g_application_run(G_APPLICATION(app), argc, argv);
    g_object_unref(app);

    return status;
}
