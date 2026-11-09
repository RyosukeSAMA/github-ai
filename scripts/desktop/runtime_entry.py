import sys

if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--delivery-worker':
        from pantheon.core.site_checker import main
        main(sys.argv[2])
    else:
        from pantheon.desktop.runner import main
        main()
