import argparse
import pygame
from random import randint, shuffle
from os import listdir
from os.path import join, exists
from dataclasses import dataclass
from json import load as json_load
from re import match
from typing import Generator


@dataclass
class Image:
    surface: pygame.Surface
    name: str


class Game:
    FRAMEWIDTH, FRAMEHEIGHT = 600, 800
    VALID_CHARS = r"[a-zA-z0-9 -]"

    def __init__(self, args):
        self.window = pygame.display.set_mode((Game.FRAMEWIDTH, Game.FRAMEHEIGHT))
        self.image_files = list(filter(lambda x: x.endswith(".png"), listdir(args.directory)))
        self.has_solmap = exists(join(args.directory, "sol_map.json"))
        self.sol_map = self._get_sol_map()

        self._subset = []
        self.subset_size = args.subset_size
        self.subset_index = 0
        self.score = 0
        n_images = len(self.image_files)
        assert self.subset_size <= n_images, f"Subset size ({self.subset_size}) must be less than or equal to the number of images ({n_images})"

        self.reveal = False
        self.select_subset = self.select_subset_no_rep if args.no_replacement else self.select_subset_with_rep
        self.select_subset()
    
    def _get_sol_map(self):
        if not self.has_solmap: return None
        with open(join(args.directory, "sol_map.json"), "r") as f:
            return json_load(f)
    
    def create_img_obj(self, img_file: str) -> Image:
        surf = self.load_img(img_file)
        return Image(surf, img_file.removesuffix(".png"))

    def load_img(self, img_file: str) -> pygame.Surface:
        surf = pygame.image.load(join(args.directory, img_file)).convert()
        max_res = max(surf.get_width(), surf.get_height())
        w = Game.FRAMEWIDTH * 0.8 * surf.get_width() / max_res
        h = Game.FRAMEWIDTH * 0.8 * surf.get_height() / max_res
        return pygame.transform.scale(surf, (w, h))
    
    def select_subset_no_rep(self) -> list[Image]:
        if len(self.image_files) == 0: exit()
        if len(self.image_files) < self.subset_size:
            self.subset_size = len(self.image_files)

        self._subset = [self.create_img_obj(self.image_files.pop(randint(0, len(self.image_files)-1))) for _ in range(self.subset_size)]
        self.subset = self.subset_gen()
        self.next_image()

    def select_subset_with_rep(self) -> list[Image]:
        self._subset = []
        contains = set()
        while len(self._subset) < self.subset_size:
            i = randint(0, len(self.image_files) - 1)
            if i in contains: continue
            img_file: str = self.image_files[i]
            self._subset.append(Image(self.load_img(img_file), img_file.removesuffix(".png")))
            contains.add(i)

        self.subset = self.subset_gen()
        self.next_image()
    
    def subset_gen(self) -> Generator[Image, None, None]:
        shuffle(self._subset)
        for img in self._subset:
            yield img
        yield None
    
    def next_image(self):
        if (img := next(self.subset)) is None:
            if self.score < self.subset_size:
                self.subset = self.subset_gen()
                self.next_image()
            else:
                
                self.select_subset()
            self.score = 0
        else:
            self.img = img
        self.text = ""
        self.reveal = False


    def run(self):
        while True:
            self.poll_events()
            self.render()
            pygame.display.update()
    
    def poll_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                quit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if self.is_correct():
                        self.score += 1
                        self.next_image()
                    elif self.reveal:
                        self.next_image()
                    else:
                        self.reveal = True
                elif event.key == pygame.K_DELETE:
                    self.text = ""
                elif event.key == pygame.K_BACKSPACE and len(self.text) > 0:
                    self.text = self.text[:-1]
                elif match(Game.VALID_CHARS, event.unicode):
                    self.text += event.unicode
                    if self.is_correct():
                        self.score += 1
                        self.next_image()

    def is_correct(self):
        txt = self.text.replace(" ", "").lower()
    
        if self.has_solmap:
            sols = self.sol_map[self.img.name.lower()]
            if self.text in sols: return True
            for sol in sols:
                if sol.replace(" ", "").lower() == txt: return True
            return False
        else:
            return txt == self.img.name.replace(" ", "").lower()

    def render(self):
        self.window.fill((255, 250, 233))
        img_offset = self.get_image_offset()
        self.window.blit(self.img.surface, img_offset)
        pygame.draw.rect(self.window, (0, 0, 0), img_offset + self.img.surface.get_size(), 2)
        self.render_text(f"{self.score}/{self.subset_size}", 25, 25, 25, (25, 25, 25))

        self.render_text(self.text, Game.FRAMEWIDTH // 2, Game.FRAMEHEIGHT - 50, 50, (25, 25, 25))
        if self.reveal:
            self.render_text(self.img.name.title(), Game.FRAMEWIDTH // 2, Game.FRAMEHEIGHT - 100, 50, (0, 250, 0))
    
    def get_image_offset(self) -> tuple[int, int]:
        return (
            (Game.FRAMEWIDTH - self.img.surface.get_width()) // 2, 
            (Game.FRAMEWIDTH - self.img.surface.get_height()) //2
            )

    def render_text(self, text, x, y, size, color, center=True):
        font = self.calculate_font(text, size)
        text = font.render(text, True, color)
        text_rect = text.get_rect()
        if center:
            text_rect.center = (x, y)
        else:
            text_rect.x = x
            text_rect.y = y
        self.window.blit(text, text_rect)
    
    def calculate_font(self, text, size):
        font = pygame.font.SysFont("Arial", size)
        while font.size(text)[0] > Game.FRAMEWIDTH:
            size -= 1
            font = pygame.font.SysFont("Arial", size)
        return font


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="cards",
        description="Flash cards")

    parser.add_argument("directory",
                        help="Directory of images",
                        type=str)
    parser.add_argument("-s", "--subset-size",
                        help="Number of images in a subset",
                        type=int,
                        default=10)
    parser.add_argument("--no-replacement", 
                        help="A flag is not replaced into the flag pool after being in a subset",
                        action="store_true")

    args = parser.parse_args()

    pygame.init()
    game = Game(args)
    game.run()
