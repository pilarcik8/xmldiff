from lxml import etree
from xmldiff import main as xmldiff_main, patch
import os


def user_input_dir_to_files():
    print("Vložte absolútnu cestu k priečinku so súbormi")

    while True:
        input_path = input()

        if not input_path or input_path.strip() == "":
            print("Zadajte platnú cestu (nie prázdnu). Skúste znova:")
            continue

        input_path = input_path.strip().strip('"')
        full_path = os.path.abspath(input_path)

        if not os.path.isdir(full_path):
            print(f"Adresár neexistuje: {full_path}. Skontrolujte cestu a skúste znova:")
            continue

        return full_path


def load_xml(full_path):
    return etree.parse(full_path)


def save_xml(tree, full_path):
    tree.write(full_path, pretty_print=True, encoding="utf-8", xml_declaration=True)


def ask_should_write_scripts():
    print("Chcete zapisovať edit scripty každej iterácie do scripts.txt? (a/n)")

    while True:
        answer = input().strip().lower()

        if answer == "a":
            return True

        if answer == "n":
            return False

        print("Prosím zadajte 'a' pre áno alebo 'n' pre nie:")


def write_iteration_scripts(scripts_path, iteration, diff_left, diff_right):
    # Súbor sa priebežne dopĺňa, aby zostal zachovaný výstup zo všetkých iterácií.
    with open(scripts_path, "a", encoding="utf-8") as file:
        file.write(f"Iterácia {iteration}\n")
        file.write("LEFT script:\n")
        if diff_left:
            for action in diff_left:
                file.write(f"{action}\n")
        else:
            file.write("(bez zmien)\n")

        file.write("RIGHT script:\n")
        if diff_right:
            for action in diff_right:
                file.write(f"{action}\n")
        else:
            file.write("(bez zmien)\n")

        file.write("\n")


def merge_three_way(base_path, left_path, right_path, result_path, scripts_path=None, iteration=None):
    base_tree = load_xml(base_path)
    left_tree = load_xml(left_path)
    right_tree = load_xml(right_path)

    diff_left = xmldiff_main.diff_trees(base_tree, left_tree)
    diff_right = xmldiff_main.diff_trees(base_tree, right_tree)

    if scripts_path is not None and iteration is not None:
        write_iteration_scripts(scripts_path, iteration, diff_left, diff_right)

    patcher = patch.Patcher()
    try:
        merged_root = patcher.patch(diff_left, base_tree)
        merged_root = patcher.patch(diff_right, merged_root)
    except Exception as ex:
        # Pri konflikte skúšame opačné poradie aplikovania patchov.
        merged_root = patcher.patch(diff_right, base_tree)
        merged_root = patcher.patch(diff_left, merged_root)    

    save_xml(etree.ElementTree(merged_root), result_path)


def main():
    DirWithFiles = user_input_dir_to_files()
    should_write_scripts = ask_should_write_scripts()
    result_dir = os.path.join(DirWithFiles, "xmldiff")
    if not os.path.exists(result_dir):
        os.mkdir(result_dir)

    scripts_path = None
    if should_write_scripts:
        scripts_path = os.path.join(result_dir, "scripts.txt")
        with open(scripts_path, "w", encoding="utf-8") as file:
            file.write("Edit scripty podľa iterácií\n\n")

    iteration = 0
    errored_files = []

    while True:

        # Očakávaná štruktúra vstupu: /<koreň>/<iterácia>/(base|left|right)<iterácia>.xml
        base_path = os.path.join(DirWithFiles, str(iteration), f"base{iteration}.xml")
        left_path = os.path.join(DirWithFiles, str(iteration), f"left{iteration}.xml")
        right_path = os.path.join(DirWithFiles, str(iteration), f"right{iteration}.xml")
        result_path = os.path.join(result_dir, f"mergedResult{iteration}.xml")

        if not (os.path.isfile(base_path) and
                os.path.isfile(left_path) and
                os.path.isfile(right_path)):

            print(f"Ukončené na iterácii: {iteration}")

            if iteration == 0:
                print("Nenájdený žiadny súbor na spracovanie.")
            else:
                print(f"Počet chybne spracovaných súborov: {len(errored_files)}")

                if errored_files:
                    print("Chybné iterácie:", ", ".join(map(str, errored_files)))

                conflict_percent = (len(errored_files) * 100.0) / iteration
                print(f"{conflict_percent:.2f}% chybne spracovaných iterací.")

            if len(errored_files) > 0:
                error_file_path = os.path.join(result_dir, "xmlDiffErrors.txt")
                with open(error_file_path, "w", encoding="utf-8") as f:
                    for item in errored_files:
                        f.write(f"{item}\n")

                print(f"Zoznam chýb uložený do: {error_file_path}")

            break

        try:
            merge_three_way(
                base_path,
                left_path,
                right_path,
                result_path,
                scripts_path=scripts_path,
                iteration=iteration,
            )
            print(f"Iterácia {iteration} spojená úspešne.")
        except Exception as ex:
            print(f"Chyba pri mergovaní v iterácii {iteration}: {ex}")
            errored_files.append(iteration)

        iteration += 1


if __name__ == "__main__":
    main()